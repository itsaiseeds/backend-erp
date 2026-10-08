"""Return orders: goods a client sends back against an order already shipped.

A return is raised by the sales person who booked the order, then accepted or
rejected by a sales admin (``docs/prd/return-orders.md``). The lifecycle is::

    PENDING -> ACCEPTED | REJECTED
    ACCEPTED -> PENDING   (revert-accept)
    REJECTED -> PENDING   (unreject)

Only a PENDING return can be edited, and only a PENDING one can be rejected, so
an accepted return is reverted before anything else happens to it.

**Accepting is inward stock.** It writes real ``InwardRawMaterial`` rows (In
Use, dated today, ``lot_no`` = the return's public id) and, when the admin
asks, ``InwardOtherMaterial`` rows booked against the recipes they pick. Every
such row points back to the return (``return_order``) and has no party. Because
they are ordinary inward rows, every stock screen, export and ledger figure
picks them up unchanged; the stock ledger records the accept as one
``RETURN_OPERATIONS`` event per product (``recording``).

**The returnable limit** per ``(product, packet_weight)`` is the packets on the
order's challan -- ``DispatchEntryItem.quantity`` x ``packaging.packets`` -- less
what any other live return already claims. A return is *live* while PENDING or
ACCEPTED, and an order may carry any number of them: the sum of their items per
``(product, packet_weight)`` never exceeds the challan's packets
(``docs/prd/multiple-return-orders.md``).

Every refusal is a ``ValidationError``, which the API renders as a 400.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum

from common.models import indian_now

from . import InventoryOperations
from .models import (
    DispatchEntryItem,
    InwardOtherMaterial,
    InwardRawMaterial,
    Order,
    OtherMaterialRecipe,
    Product,
    ReturnOrder,
    ReturnOrderItem,
    Status,
    StatusIds,
    StockEventDetail,
    StockEventType,
)
from .models.ReturnOrder import LIVE_RETURN_STATUS_IDS
from .NotificationOperations import NotificationEvent, notify_return_order_event
from .ProductOperations import assert_products_usable
from .StockLedgerOperations import recording

if TYPE_CHECKING:
    from authentication.models import User

WEIGHT_QUANT = Decimal("0.001")
PRICE_QUANT = Decimal("0.01")
# ``InwardOtherMaterial.quantity`` is numeric(10, 3): refuse what cannot be stored
# rather than let the database answer with a 500.
MAX_OTHER_MATERIAL_QUANTITY = Decimal("10000000")

# Orders whose goods have left the warehouse: the only ones that can come back.
RETURNABLE_ORDER_STATUS_IDS = frozenset({StatusIds.DISPATCHED, StatusIds.DELIVERED})

PoolKey = tuple[int, Decimal]


def _weight(value) -> Decimal:
    return Decimal(value).quantize(WEIGHT_QUANT)


def _line_label(product: Product, packet_weight: Decimal) -> str:
    return f"'{product.name}' {packet_weight}kg packets"


def _status_code(status_id: int) -> str:
    return StatusIds(status_id).name


# -- Locking and guards -------------------------------------------------------


def lock_order(order: Order) -> Order:
    """Lock ``order``'s row, then reload it with its status.

    Creating, editing, accepting and un-rejecting a return all take this lock
    first, so two of them for the same order run one after the other and the
    limit (and, for a v1 create, the one-live-return rule) is checked against
    what the last one left. It is the lock ``GetOrderView.get_locked_order`` takes for every order
    lifecycle verb, so a ``revert-dispatch`` is serialised against them too.

    The lock is taken on the bare row and the joined load runs afterwards, the
    same way ``get_locked_order`` does. Must be called inside
    ``transaction.atomic``.
    """
    pk = Order.objects.select_for_update().filter(pk=order.pk).values_list("pk", flat=True).first()
    if pk is None:
        raise ValidationError("This order no longer exists.")
    return Order.objects.select_related("status", "client").get(pk=pk)


def live_returns(order: Order, exclude: ReturnOrder | None = None):
    """The live (PENDING or ACCEPTED) returns of ``order``, minus ``exclude``."""
    queryset = ReturnOrder.objects.filter(
        order=order, status_id__in=[int(s) for s in LIVE_RETURN_STATUS_IDS]
    )
    if exclude is not None:
        queryset = queryset.exclude(pk=exclude.pk)
    return queryset


def challan_packets(order: Order) -> dict[PoolKey, int]:
    """Packets that left on ``order``'s challan, per ``(product_id, packet_weight)``."""
    rows = DispatchEntryItem.objects.filter(
        dispatch_entry__order=order,
        dispatch_entry__is_deleted=False,
        product_packaging__isnull=False,
    ).values_list(
        "quantity",
        "product_packaging__packets",
        "product_packaging__product_id",
        "product_packaging__packet_weight",
    )
    dispatched: dict[PoolKey, int] = {}
    for quantity, packets_per_bag, product_id, packet_weight in rows:
        key = (product_id, _weight(packet_weight))
        dispatched[key] = dispatched.get(key, 0) + quantity * packets_per_bag
    return dispatched


def returnable_packets(order: Order, exclude: ReturnOrder | None = None) -> dict[PoolKey, int]:
    """``{(product_id, packet_weight): packets}`` still returnable on ``order``.

    The challan's packets, less the items of any live return other than
    ``exclude``. A pair whose packets are all claimed stays in the dict at 0.
    """
    remaining = challan_packets(order)
    claimed = (
        ReturnOrderItem.objects.filter(
            return_order__in=live_returns(order, exclude),
        )
        .values("product_id", "packet_weight")
        .annotate(packets=Sum("packets"))
    )
    for row in claimed:
        key = (row["product_id"], _weight(row["packet_weight"]))
        if key in remaining:
            remaining[key] -= row["packets"]
    return remaining


def assert_order_returnable(
    order: Order, exclude: ReturnOrder | None = None, *, single_live: bool = False
) -> None:
    """Raise unless ``order`` may take a (new or restored) return.

    Its status must be DISPATCHED or DELIVERED. With ``single_live`` (the v1
    Android create) it must also have no live return besides ``exclude``. Without
    it any number of live returns may coexist; ``assert_items_within_limit``
    keeps their sum within the challan.
    """
    if order.status_id not in RETURNABLE_ORDER_STATUS_IDS:
        raise ValidationError(
            {
                "order": (
                    f"Cannot return an order that is {order.status.code}. "
                    "Only a DISPATCHED or DELIVERED order can have a return."
                )
            }
        )
    if not single_live:
        return
    other = live_returns(order, exclude).first()
    if other is not None:
        raise ValidationError(
            {
                "order": (
                    f"{order.public_id} already has a live return ({other.public_id}, "
                    f"{_status_code(other.status_id)}). Only one is allowed at a time."
                )
            }
        )


def assert_items_within_limit(
    order: Order, items: list[dict], exclude: ReturnOrder | None = None
) -> None:
    """Raise unless ``items`` can be returned against ``order``'s challan.

    Each item is ``{"product", "packet_weight", "packets", ...}``. The list must
    be non-empty with no ``(product, packet_weight)`` twice; each pair must be on
    the challan; and no pair may exceed the packets still returnable.
    """
    if not items:
        raise ValidationError({"items": "A return must have at least one item."})

    keys = [(item["product"].pk, _weight(item["packet_weight"])) for item in items]
    if len(set(keys)) != len(keys):
        raise ValidationError({"items": "The same product and packet weight is listed twice."})

    limits = returnable_packets(order, exclude)
    problems = []
    for item, key in zip(items, keys, strict=True):
        label = _line_label(item["product"], key[1])
        if key not in limits:
            problems.append(f"{label} were not dispatched on this order")
        elif item["packets"] > limits[key]:
            problems.append(
                f"{label}: returning {item['packets']} but only {limits[key]} can be returned"
            )
    if problems:
        raise ValidationError({"items": f"Invalid return -- {'; '.join(problems)}."})


def assert_return_status(ret: ReturnOrder, allowed: frozenset[int], action: str) -> None:
    """Guard a return's lifecycle verb on its current status."""
    if ret.status_id not in allowed:
        allowed_codes = ", ".join(sorted(_status_code(s) for s in allowed))
        raise ValidationError(
            {
                "status": (
                    f"Cannot {action} a return that is {_status_code(ret.status_id)}. "
                    f"Allowed: {allowed_codes}."
                )
            }
        )


PENDING_ONLY = frozenset({StatusIds.RETURN_PENDING})
ACCEPTED_ONLY = frozenset({StatusIds.RETURN_ACCEPTED})
REJECTED_ONLY = frozenset({StatusIds.RETURN_REJECTED})


def _assert_admin(admin: User | None) -> None:
    if not (admin is not None and (admin.is_admin_user or admin.is_superuser)):
        raise PermissionDenied("Returns can only be accepted or rejected by a sales admin.")


# -- Create and edit ----------------------------------------------------------


@transaction.atomic
def create_return_order(
    order: Order,
    *,
    return_date: date | None,
    items: list[dict],
    actor: User,
    single_live: bool = False,
) -> ReturnOrder:
    """Raise a PENDING return against ``order``.

    ``items`` is ``[{"product", "packet_weight", "packets", "price_per_packet"}]``.
    The order row is locked first, so two creates for the same order cannot both
    claim the same packets. ``single_live`` (Android v1) also refuses when the
    order already has a live return.
    """
    order = lock_order(order)
    assert_order_returnable(order, single_live=single_live)
    assert_items_within_limit(order, items)

    ret = ReturnOrder(
        order=order,
        status=Status.by_id(StatusIds.RETURN_PENDING),
        created_by=actor,
    )
    if return_date is not None:
        ret.return_date = return_date
    ret.full_clean()
    ret.save()
    _sync_items(ret, items, actor)
    return ret


@transaction.atomic
def update_return_order(
    ret: ReturnOrder, *, return_date: date | None, items: list[dict], actor: User
) -> ReturnOrder:
    """Replace a PENDING return's lines (and optionally its date).

    Same rules as :func:`create_return_order`; ``items`` is a full declarative
    replacement, so a line left out is removed.
    """
    order = lock_order(ret.order)
    ret.refresh_from_db()
    assert_return_status(ret, PENDING_ONLY, "edit")
    assert_order_returnable(order)
    assert_items_within_limit(order, items, exclude=ret)

    if return_date is not None:
        ret.return_date = return_date
        ret.full_clean()
        ret.save(update_fields=["return_date", "updated_at"])
    _sync_items(ret, items, actor)
    return ret


def _sync_items(ret: ReturnOrder, items: list[dict], actor: User) -> list[ReturnOrderItem]:
    """Make ``ret``'s lines exactly ``items``.

    Existing lines are looked up through ``all_objects`` because the unique key
    ``(return_order, product, packet_weight)`` is **not** soft-delete aware: a
    pair that was removed and later put back must have its row restored, not
    inserted a second time (the same reason ``_sync_order_items`` does it).
    """
    existing = {
        (line.product_id, _weight(line.packet_weight)): line
        for line in ReturnOrderItem.all_objects.filter(return_order=ret)
    }
    # A frozen product's line may be removed or lowered but not added back or raised;
    # a soft-deleted line being restored counts as added.
    assert_products_usable(
        {
            item["product"].pk
            for item in items
            if (key := (item["product"].pk, _weight(item["packet_weight"]))) not in existing
            or existing[key].is_deleted
            or item["packets"] > existing[key].packets
        },
        field="items",
        action="have return lines added or raised",
        subject="this return",
    )
    kept: list[ReturnOrderItem] = []
    for item in items:
        key = (item["product"].pk, _weight(item["packet_weight"]))
        line = existing.pop(key, None)
        if line is None:
            line = ReturnOrderItem(
                return_order=ret,
                product=item["product"],
                packet_weight=key[1],
                created_by=actor,
            )
        else:
            line.restore()
        line.packets = item["packets"]
        line.price_per_packet = item["price_per_packet"]
        line.full_clean()
        line.save()
        kept.append(line)
    for stale in existing.values():
        stale.mark_deleted(actor)
    return kept


# -- Recipe picker ------------------------------------------------------------


def _recipe_option_payload(recipe: OtherMaterialRecipe) -> dict:
    material_type = recipe.material_type
    return {
        "public_id": recipe.public_id,
        "material_type": {
            "id": material_type.id,
            "name": material_type.name,
            "unit_type": material_type.unit_type,
        },
        "quantity": str(recipe.quantity),
        "is_deleted": recipe.is_deleted,
        "created_at": recipe.created_at.isoformat(),
        "deleted_at": recipe.deleted_at.isoformat() if recipe.deleted_at else None,
    }


def return_order_recipe_options(ret: ReturnOrder) -> list[dict]:
    """For each line of ``ret``, every recipe of that line's ``(product, weight)``.

    Soft-deleted recipes are included: stock booked against a since-replaced
    recipe still counts, so the admin may pick one. The recipe picker endpoint
    renders this.
    """
    lines = []
    for item in ret.items.select_related("product"):
        recipes = (
            OtherMaterialRecipe.all_objects.filter(
                product=item.product, packet_weight=item.packet_weight
            )
            .select_related("material_type")
            .order_by("material_type__name", "is_deleted", "created_at", "id")
        )
        lines.append(
            {
                "product": {
                    "public_id": item.product.public_id,
                    "name": item.product.name,
                },
                "packet_weight": str(_weight(item.packet_weight)),
                "packets": item.packets,
                "recipes": [_recipe_option_payload(recipe) for recipe in recipes],
            }
        )
    return lines


# -- Accept / revert-accept ---------------------------------------------------


def _resolve_recipes(
    items: list[ReturnOrderItem], include_other: bool, recipe_public_ids: Iterable[str] | None
) -> dict[ReturnOrderItem, list[OtherMaterialRecipe]]:
    """Match the chosen recipes to the return's lines, or raise.

    ``include_other`` false means no recipes may be sent. True means every line
    must get at least one recipe, each recipe must belong to some line's
    ``(product, packet_weight)``, and a line may have at most one recipe per
    material type. Live and soft-deleted recipes are both accepted.
    """
    public_ids = list(recipe_public_ids or [])
    if not include_other:
        if public_ids:
            raise ValidationError(
                {
                    "recipe_public_ids": (
                        "recipe_public_ids must be empty when "
                        "include_in_other_raw_materials is false."
                    )
                }
            )
        return {}

    recipes = {
        recipe.public_id: recipe
        for recipe in OtherMaterialRecipe.all_objects.filter(
            public_id__in=public_ids
        ).select_related("material_type", "product")
    }
    unknown = [public_id for public_id in public_ids if public_id not in recipes]
    if unknown:
        raise ValidationError({"recipe_public_ids": f"Unknown recipe(s): {', '.join(unknown)}."})

    by_pair: dict[PoolKey, ReturnOrderItem] = {
        (item.product_id, _weight(item.packet_weight)): item for item in items
    }
    chosen: dict[ReturnOrderItem, list[OtherMaterialRecipe]] = {item: [] for item in items}
    stray = []
    for public_id in public_ids:
        recipe = recipes[public_id]
        item = by_pair.get((recipe.product_id, _weight(recipe.packet_weight)))
        if item is None:
            stray.append(public_id)
        else:
            chosen[item].append(recipe)
    if stray:
        raise ValidationError(
            {"recipe_public_ids": (f"Recipe(s) {', '.join(stray)} match no line of this return.")}
        )

    for item, picked in chosen.items():
        types = [recipe.material_type_id for recipe in picked]
        if len(set(types)) != len(types):
            raise ValidationError(
                {
                    "recipe_public_ids": (
                        f"{_line_label(item.product, _weight(item.packet_weight))}: "
                        "at most one recipe per material type."
                    )
                }
            )

    uncovered = [
        _line_label(item.product, _weight(item.packet_weight))
        for item, picked in chosen.items()
        if not picked
    ]
    if uncovered:
        raise ValidationError(
            {
                "recipe_public_ids": (
                    f"Every line needs at least one recipe. Not covered: {'; '.join(uncovered)}."
                )
            }
        )
    return chosen


@transaction.atomic
def accept_return_order(
    ret: ReturnOrder,
    *,
    include_other: bool,
    recipe_public_ids: Iterable[str] | None,
    admin: User,
) -> ReturnOrder:
    """Accept a PENDING return: its raw kg goes In Use, and optionally its packing.

    The limit is re-checked against the challan. Each line books one In Use
    ``InwardRawMaterial`` for ``packets x packet_weight`` kg; when
    ``include_other`` is true it also books, for each recipe the admin picked,
    ``recipe.quantity x packets`` of that recipe's material. All of it is dated
    today (the accept day), has no party, and points back at ``ret``.

    One ``RETURN_OPERATIONS`` / ``RETURN_ACCEPTED`` ledger event is written per
    product the return touches.
    """
    _assert_admin(admin)
    order = lock_order(ret.order)
    ret.refresh_from_db()
    assert_return_status(ret, PENDING_ONLY, "accept")
    assert_order_returnable(order)

    items = list(ret.items.select_related("product"))
    assert_items_within_limit(
        order,
        [
            {
                "product": item.product,
                "packet_weight": item.packet_weight,
                "packets": item.packets,
            }
            for item in items
        ],
        exclude=ret,
    )
    chosen = _resolve_recipes(items, include_other, recipe_public_ids)

    today = InventoryOperations.today()
    product_ids = {item.product_id for item in items}
    with recording(
        StockEventType.RETURN_OPERATIONS,
        StockEventDetail.RETURN_ACCEPTED,
        product_ids,
        source=ret,
        actor=admin,
    ):
        # Accepting books inward lots for these products, so it is refused while any
        # of them is frozen (``Product.is_usable``).
        assert_products_usable(
            product_ids, field="status", action="be accepted", subject="this return"
        )
        # A material that only a deleted recipe uses is not among the types the
        # recording locked, so lock the ones about to be booked as well.
        InventoryOperations._lock_materials(
            product_ids,
            {recipe.material_type_id for picked in chosen.values() for recipe in picked},
        )
        in_use = Status.by_id(StatusIds.IN_USE)
        for item in items:
            InwardRawMaterial.objects.create(
                product=item.product,
                party=None,
                return_order=ret,
                lot_no=ret.public_id,
                farmer_name=f"Return Order ({ret.order.public_id})",
                quantity_kg=item.kg,
                status=in_use,
                effective_date=today,
                created_by=admin,
            )
            for recipe in chosen.get(item, []):
                quantity = recipe.quantity * item.packets
                if quantity >= MAX_OTHER_MATERIAL_QUANTITY:
                    raise ValidationError(
                        {
                            "recipe_public_ids": (
                                f"{recipe.public_id} x {item.packets} packets is too large "
                                "a quantity to book."
                            )
                        }
                    )
                InwardOtherMaterial.objects.create(
                    party=None,
                    return_order=ret,
                    recipe=recipe,
                    quantity=quantity,
                    effective_date=today,
                    created_by=admin,
                )

        ret.status = Status.by_id(StatusIds.RETURN_ACCEPTED)
        ret.include_in_other_raw_materials = include_other
        ret.verified_by = admin
        ret.verified_at = indian_now()
        ret.full_clean()
        ret.save(
            update_fields=[
                "status",
                "include_in_other_raw_materials",
                "verified_by",
                "verified_at",
                "updated_at",
            ]
        )
    notify_return_order_event(ret, NotificationEvent.RETURN_ACCEPTED, actor=admin)
    return ret


@transaction.atomic
def revert_accept_return_order(ret: ReturnOrder, *, admin: User) -> ReturnOrder:
    """Undo an accept: remove the inward rows it booked and go back to PENDING.

    Refused (400, nothing changes) when removing the raw kilograms or the packing
    material would leave their available stock below zero -- i.e. it has since
    been packed or used. That is the guard deleting an in-use lot applies
    (``InventoryOperations.guard_stock_deletion``).

    The lots are soft-deleted with one queryset update rather than through
    ``mark_deleted``: a return's lots refuse every direct delete, and
    ``guard_soft_delete`` would open a second ``recording`` inside this one,
    writing the removal as two events. The guard is called directly with no
    ledger of its own, so this ``RETURN_ACCEPT_REVERTED`` event is the only one.
    """
    _assert_admin(admin)
    lock_order(ret.order)
    ret.refresh_from_db()
    assert_return_status(ret, ACCEPTED_ONLY, "revert the accept of")

    raw_lots = InwardRawMaterial.objects.filter(return_order=ret)
    other_lots = InwardOtherMaterial.objects.filter(return_order=ret)
    product_ids = set(raw_lots.values_list("product_id", flat=True)) | set(
        other_lots.values_list("recipe__product_id", flat=True)
    )
    material_type_ids = set(other_lots.values_list("recipe__material_type_id", flat=True))

    with recording(
        StockEventType.RETURN_OPERATIONS,
        StockEventDetail.RETURN_ACCEPT_REVERTED,
        product_ids,
        source=ret,
        actor=admin,
    ):
        # The lots are removed by a queryset update, which skips their own delete
        # guard, so the freeze is checked here: a frozen product's existing rows
        # are read-only.
        assert_products_usable(
            product_ids,
            field="status",
            action="have its accept reverted",
            subject="this return",
        )

        def perform() -> None:
            now = indian_now()
            removal = {
                "is_deleted": True,
                "deleted_at": now,
                "deleted_by": admin,
                "updated_at": now,
            }
            raw_lots.update(**removal)
            other_lots.update(**removal)

        InventoryOperations.guard_stock_deletion(
            perform, product_ids=product_ids, material_type_ids=material_type_ids
        )

        ret.status = Status.by_id(StatusIds.RETURN_PENDING)
        ret.include_in_other_raw_materials = None
        ret.verified_by = None
        ret.verified_at = None
        ret.full_clean()
        ret.save(
            update_fields=[
                "status",
                "include_in_other_raw_materials",
                "verified_by",
                "verified_at",
                "updated_at",
            ]
        )
    return ret


# -- Reject / unreject --------------------------------------------------------


@transaction.atomic
def reject_return_order(ret: ReturnOrder, *, admin: User) -> ReturnOrder:
    """Reject a PENDING return. No stock moves, so no ledger event is written.

    An ACCEPTED return must be reverted first.
    """
    _assert_admin(admin)
    lock_order(ret.order)
    ret.refresh_from_db()
    assert_return_status(ret, PENDING_ONLY, "reject")
    ret.status = Status.by_id(StatusIds.RETURN_REJECTED)
    ret.rejected_by = admin
    ret.rejected_at = indian_now()
    ret.full_clean()
    ret.save(update_fields=["status", "rejected_by", "rejected_at", "updated_at"])
    notify_return_order_event(ret, NotificationEvent.RETURN_REJECTED, actor=admin)
    return ret


@transaction.atomic
def unreject_return_order(ret: ReturnOrder, *, admin: User) -> ReturnOrder:
    """Bring a REJECTED return back to PENDING.

    A rejected return was out of the way -- it did not count toward the limit and
    another return may have been raised since -- so the order must still be
    returnable with no other live return, and the items must still fit.
    """
    _assert_admin(admin)
    order = lock_order(ret.order)
    ret.refresh_from_db()
    assert_return_status(ret, REJECTED_ONLY, "unreject")
    assert_order_returnable(order)
    assert_items_within_limit(
        order,
        [
            {
                "product": item.product,
                "packet_weight": item.packet_weight,
                "packets": item.packets,
            }
            for item in ret.items.select_related("product")
        ],
        exclude=ret,
    )
    ret.status = Status.by_id(StatusIds.RETURN_PENDING)
    ret.rejected_by = None
    ret.rejected_at = None
    ret.full_clean()
    ret.save(update_fields=["status", "rejected_by", "rejected_at", "updated_at"])
    return ret


# -- Payloads -----------------------------------------------------------------


def _item_payload(item: ReturnOrderItem) -> dict:
    return {
        "product": {"public_id": item.product.public_id, "name": item.product.name},
        "packet_weight": str(_weight(item.packet_weight)),
        "packets": item.packets,
        "kg": str(item.kg),
        "price_per_packet": str(item.price_per_packet),
        "line_total": str(item.line_total),
    }


def _user_ref(user: User | None) -> dict | None:
    return {"id": user.pk, "name": user.display_name} if user is not None else None


def _list_fields(ret: ReturnOrder) -> dict:
    return {
        "public_id": ret.public_id,
        "status": ret.status.code,
        "return_date": ret.return_date.isoformat(),
        "created_at": ret.created_at.isoformat(),
        "order": {
            "public_id": ret.order.public_id,
            "status": ret.order.status.code,
        },
        "client": {
            "public_id": ret.order.client.public_id,
            "company_name": ret.order.client.company_name,
        },
        "created_by": _user_ref(ret.created_by),
        "verified_by": _user_ref(ret.verified_by),
        "rejected_by": _user_ref(ret.rejected_by),
        "items": [_item_payload(item) for item in ret.items.all()],
        "total_kg": str(ret.total_kg),
        "total_amount": str(ret.total_amount),
    }


def return_order_list_payload(ret: ReturnOrder) -> dict:
    """Compact dict for a return list row: status, dates, who, what and how much.

    Reads ``items`` off the instance, so ``prefetch_related`` of the items (with
    their product) and ``select_related`` of the status, order, client and
    actors keeps it query-free.
    """
    return _list_fields(ret)


def return_order_payload(ret: ReturnOrder) -> dict:
    """Full dict for one return: the list fields plus accept/reject details.

    ``inward_raw_materials`` / ``inward_other_materials`` are the public ids of
    the lots an accept booked; empty unless the return is ACCEPTED.
    """
    return {
        **_list_fields(ret),
        "include_in_other_raw_materials": ret.include_in_other_raw_materials,
        "verified_at": ret.verified_at.isoformat() if ret.verified_at else None,
        "rejected_at": ret.rejected_at.isoformat() if ret.rejected_at else None,
        "inward_raw_materials": list(
            InwardRawMaterial.objects.filter(return_order=ret)
            .order_by("id")
            .values_list("public_id", flat=True)
        ),
        "inward_other_materials": list(
            InwardOtherMaterial.objects.filter(return_order=ret)
            .order_by("id")
            .values_list("public_id", flat=True)
        ),
    }


def live_return_orders(order: Order) -> list[ReturnOrder]:
    """``order``'s live returns, newest first.

    Reads ``order.live_return_orders`` when ``order_detail_queryset`` prefetched
    it (``Prefetch(..., to_attr="live_return_orders")``, ordered newest first),
    and queries otherwise. A REJECTED return is never live, so never appears.
    """
    prefetched = getattr(order, "live_return_orders", None)
    if prefetched is not None:
        return list(prefetched)
    return list(
        live_returns(order)
        .select_related(
            "status",
            "order__status",
            "order__client",
            "created_by",
            "verified_by",
            "rejected_by",
        )
        .prefetch_related("items__product")
        .order_by("-created_at", "-id")
    )


def live_return_order(order: Order) -> ReturnOrder | None:
    """The newest live return of ``order``, if any (v1 / compatibility callers)."""
    live = live_return_orders(order)
    return live[0] if live else None


def order_return_payload(order: Order) -> dict | None:
    """The ``return_order`` block of an order's detail payload, or null."""
    ret = live_return_order(order)
    return return_order_payload(ret) if ret is not None else None


# -- Android prefill ----------------------------------------------------------


def return_order_prefill_payload(order: Order, *, many: bool = False) -> dict:
    """What the return screen needs for ``order``: its summary, live return(s), the lines.

    v1 (default) emits ``return_order`` -- the newest live return or null; with
    ``many=True`` (v2) it emits ``return_orders`` -- every live return, newest
    first.

    ``lines`` has one entry per ``(product, packet_weight)`` on the challan:
    the packets dispatched, the packets still returnable, and a suggested
    ``price_per_packet`` -- the order line's bag price divided by the packets in
    the bag (the first challan line of the pair when several bags share it).
    """
    limits = returnable_packets(order)
    dispatched = challan_packets(order)
    first_price: dict[PoolKey, Decimal] = {}
    products: dict[int, Product] = {}
    rows = (
        DispatchEntryItem.objects.filter(
            dispatch_entry__order=order,
            dispatch_entry__is_deleted=False,
            product_packaging__isnull=False,
        )
        .select_related("product_packaging__product")
        .order_by("id")
    )
    for row in rows:
        packaging = row.product_packaging
        if packaging is None:  # a loose (custom-order) line; the query excludes them
            continue
        key = (packaging.product_id, _weight(packaging.packet_weight))
        products[packaging.product_id] = packaging.product
        first_price.setdefault(
            key,
            (row.negotiated_selling_price / packaging.packets).quantize(
                PRICE_QUANT, rounding=ROUND_HALF_UP
            ),
        )
    lines = [
        {
            "product": {
                "public_id": products[key[0]].public_id,
                "name": products[key[0]].name,
            },
            "packet_weight": str(key[1]),
            "dispatched_packets": dispatched[key],
            "returnable_packets": limits[key],
            "suggested_price_per_packet": str(first_price[key]),
        }
        for key in sorted(dispatched, key=lambda k: (products[k[0]].name, k[1]))
    ]
    live = live_return_orders(order)
    returns_block = (
        {"return_orders": [return_order_payload(r) for r in live]}
        if many
        else {"return_order": return_order_payload(live[0]) if live else None}
    )
    return {
        "order": {
            "public_id": order.public_id,
            "status": order.status.code,
            "client": {
                "public_id": order.client.public_id,
                "company_name": order.client.company_name,
            },
        },
        **returns_block,
        "lines": lines,
    }


def items_from_payload(rows: Iterable[Mapping]) -> list[dict]:
    """Normalize validated request rows into the ``items`` shape the operations take."""
    return [
        {
            "product": row["product"],
            "packet_weight": _weight(row["packet_weight"]),
            "packets": row["packets"],
            "price_per_packet": row["price_per_packet"],
        }
        for row in rows
    ]
