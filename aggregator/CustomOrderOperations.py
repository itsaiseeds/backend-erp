"""Custom-order lifecycle helpers for the ``aggregator`` sales domain.

A custom order is the loose-packet counterpart of a normal :class:`Order`: its
lines are counted in loose packets and drawn from the ``(product, packet_weight)``
loose pool, and it may be booked only by a sales admin. It is a standalone
record with no foreign key to ``Order``.

Every line names a ``packet_weight`` because a loose packet has a definite
weight: 5 x 1kg and 5 x 500g draw on different pools and are worth different
money.

Custom orders are exposed to the frontend by their ``public_id`` (``CORD-…``, or
``WORD-…`` for a waste order);
payloads never include the internal primary key.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction

from common.models import indian_now

from .ClientChildOrgOperations import child_org_payload, child_org_summary_payload
from .ClientOperations import (
    client_payload,
    client_summary_payload,
    order_city_payload,
)
from .models import (
    Address,
    City,
    Client,
    ClientChildOrg,
    CustomOrder,
    CustomOrderItem,
    DispatchDetails,
    OrderUnit,
    PrivateDispatchDetails,
    Product,
    Status,
    StatusIds,
    StockEventDetail,
    StockEventType,
)
from .ProductOperations import assert_products_usable
from .StockLedgerOperations import custom_order_product_ids, recording

if TYPE_CHECKING:
    from authentication.models import User


def assert_loose_stock_covers(
    needed: Mapping[tuple[Product, Decimal], int],
    action: str = "create",
    *,
    held: Mapping[tuple[Product, Decimal], int] | None = None,
) -> None:
    """Raise unless the loose pools can supply ``needed`` packets per pool.

    ``needed`` maps ``(product, packet_weight)`` to the packets the custom order
    takes from that exact pool -- a 1kg line is never filled from 500g stock --
    summed over **all** its lines, so two lines for the same pool cannot each
    fit on their own while together exceeding it.

    ``held`` is what the order already reserves (an existing CONFIRMED order's
    current lines, when it is being edited). ``available_loose_packets`` has
    already netted it off, so it is added back before comparing -- otherwise the
    order would be counted against itself. A pool whose need does not exceed
    what is held asks for nothing new and is not checked, so shrinking an order
    is never refused. The same contract as ``OrderOperations.assert_stock_covers``.

    The pools are locked first (:func:`InventoryOperations.lock_loose_pools`)
    and stay locked until the caller's transaction commits the order, so two
    orders written at once cannot both spend the same packets. Callers must be
    inside ``transaction.atomic``: ``create_custom_order``,
    ``sync_custom_order_items`` and the admin's add form, which Django already
    runs atomically.
    """
    from . import InventoryOperations

    held = held or {}
    increases = {
        pool: packets for pool, packets in needed.items() if packets > held.get(pool, 0)
    }
    if not increases:
        return

    InventoryOperations.lock_loose_pools(product.id for product, _ in increases)
    shortages = []
    for (product, packet_weight), packets in increases.items():
        available = InventoryOperations.available_loose_packets(
            product, packet_weight
        ) + held.get((product, packet_weight), 0)
        if packets > available:
            shortages.append(
                f"{product.name} @ {packet_weight}kg: need {packets}, have {available}"
            )
    if shortages:
        raise ValidationError(
            {
                "packets": (
                    f"Not enough loose-packet stock to {action} this custom order -- "
                    f"{'; '.join(shortages)}."
                )
            }
        )


def loose_requirements(items: Iterable[dict]) -> dict[tuple[Product, Decimal], int]:
    """Sum ``items``' packets per ``(product, packet_weight)`` pool."""
    needed: dict[tuple[Product, Decimal], int] = {}
    for item in items:
        pool = (item["product"], item["packet_weight"])
        needed[pool] = needed.get(pool, 0) + item["packets"]
    return needed


def assert_order_kind(order: CustomOrder, made_from_waste: bool, action: str) -> None:
    """Raise unless ``order`` is a waste order (or a packet order), as ``action`` needs.

    A waste order and a packet order share one table but not one set of rules
    (kg lines against the waste pool, packet lines against the loose pools), so
    each verb refuses the other kind rather than misreading its lines.
    """
    if order.made_from_waste == made_from_waste:
        return
    if made_from_waste:
        raise ValidationError(
            {"made_from_waste": f"Cannot {action} a custom order as a waste order."}
        )
    raise ValidationError(
        {"made_from_waste": f"Cannot {action} a waste order as a custom order."}
    )


@transaction.atomic
def create_custom_order(
    *,
    client: Client,
    delivery_address: Address,
    actor: User,
    items: Iterable[dict],
    special_comments: str = "",
    expected_delivery_date=None,
    booked_for: ClientChildOrg | None = None,
) -> CustomOrder:
    """Create a custom order and its loose-packet lines atomically.

    A custom order has **no separate verification step**: it is an admin
    instrument, so creating it *is* verifying it -- the order is born
    ``CONFIRMED`` with ``verified_by``/``verified_at`` set to the creating admin.

    ``actor`` must be a sales admin (enforced in ``CustomOrder.clean``). Each
    entry in ``items`` is ``{"product", "packet_weight", "packets"}`` plus an
    optional ``"negotiated_selling_price"`` (per packet); when omitted the line
    is priced at ``product.price_for_weight(packet_weight)``.

    **Stock gate:** see :func:`assert_loose_stock_covers`. Because the order
    confirms immediately, availability is checked *before* it reserves.
    """
    items = list(items)
    with recording(
        StockEventType.ORDER_CONFIRMED,
        StockEventDetail.CUSTOM_ORDER_CREATED,
        {item["product"].pk for item in items},
        actor=actor,
    ) as rec:
        assert_products_usable(
            {item["product"].pk for item in items},
            field="items",
            action="be ordered",
            subject="this custom order",
        )
        assert_loose_stock_covers(loose_requirements(items))

        order = CustomOrder(
            client=client,
            delivery_address=delivery_address,
            status=Status.by_id(StatusIds.CONFIRMED),
            created_by=actor,
            verified_by=actor,
            verified_at=indian_now(),
            special_comments=special_comments,
            booked_for=booked_for,
        )
        if expected_delivery_date is not None:
            order.expected_delivery_date = expected_delivery_date
        order.full_clean()
        order.save()
        rec.source = order

        for item in items:
            add_custom_order_item(
                order,
                product=item["product"],
                packet_weight=item["packet_weight"],
                negotiated_selling_price=item.get("negotiated_selling_price"),
                packets=item["packets"],
                actor=actor,
            )
    return order


def add_custom_order_item(
    order: CustomOrder,
    *,
    product: Product,
    packet_weight,
    packets: int,
    actor: User,
    negotiated_selling_price=None,
) -> CustomOrderItem:
    """Add a loose-packet line to ``order`` for one ``(product, packet_weight)`` pool.

    ``negotiated_selling_price`` overrides the per-packet price for this line
    only; omit it to charge ``product.price_for_weight(packet_weight)``.

    Because ``Product.selling_price`` is a per-kilogram rate, that default is
    weight-correct on its own: a 500g line prefills at half a 1kg line.
    """
    if negotiated_selling_price is None:
        negotiated_selling_price = product.price_for_weight(packet_weight)
    item = CustomOrderItem(
        custom_order=order,
        product=product,
        packet_weight=packet_weight,
        negotiated_selling_price=negotiated_selling_price,
        packets=packets,
        created_by=actor,
    )
    item.full_clean()
    item.save()
    return item


def update_custom_order_status(order: CustomOrder, status: StatusIds) -> CustomOrder:
    order.status = Status.by_id(status)
    order.full_clean()
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def attach_dispatch_details(
    order: CustomOrder,
    *,
    dispatched_by: User,
    dispatch_date,
    from_city: City,
    to_city: City,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
    lr_number: str = "",
) -> DispatchDetails:
    """Record a third-party dispatch and link it to the custom order.

    Writes the same ``DispatchDetails`` table as the packaged-order path, so it
    carries the same mandatory driver and vehicle details; ``lr_number`` is the
    one field the transporter may issue later.
    """
    dispatch = DispatchDetails(
        client=order.client,
        dispatched_by=dispatched_by,
        dispatch_date=dispatch_date,
        from_city=from_city,
        to_city=to_city,
        driver_name=driver_name,
        driver_number=driver_number,
        vehicle_number=vehicle_number,
        lr_number=lr_number,
    )
    dispatch.full_clean()
    dispatch.save()

    order.dispatch_details = dispatch
    order.private_dispatch_details = None
    order.full_clean()
    order.save(update_fields=["dispatch_details", "private_dispatch_details", "updated_at"])
    return dispatch


@transaction.atomic
def attach_private_dispatch_details(
    order: CustomOrder,
    *,
    dispatched_by: User,
    dispatch_date,
    from_city: City,
    to_city: City,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
) -> PrivateDispatchDetails:
    """Record an own-vehicle dispatch and link it to the custom order."""
    dispatch = PrivateDispatchDetails(
        client=order.client,
        dispatched_by=dispatched_by,
        dispatch_date=dispatch_date,
        from_city=from_city,
        to_city=to_city,
        driver_name=driver_name,
        driver_number=driver_number,
        vehicle_number=vehicle_number,
    )
    dispatch.full_clean()
    dispatch.save()

    order.private_dispatch_details = dispatch
    order.dispatch_details = None
    order.full_clean()
    order.save(update_fields=["dispatch_details", "private_dispatch_details", "updated_at"])
    return dispatch


DISPATCHABLE_CUSTOM_ORDER_STATUS_CODES = frozenset({StatusIds.CONFIRMED.name})


@transaction.atomic
def dispatch_custom_order(
    order: CustomOrder,
    *,
    actor: User,
    from_city: City,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
    lot_numbers: dict[tuple[str, Decimal], str],
) -> CustomOrder:
    """Record a dispatch against a CONFIRMED custom order and move it to DISPATCHED.

    The custom-order counterpart of ``OrderOperations.dispatch_order``, with
    one difference: a custom order has no transport agency, so it always goes
    on our own vehicle and lands on ``PrivateDispatchDetails``. That is also
    why there is no LR number to record for one afterwards.

    The dispatch date is today and the destination the city of the order's own
    delivery address, as for an order. ``lot_numbers`` maps each line's
    ``(product public id, packet_weight)`` to the batch those packets came from
    and must name every line exactly once -- the dispatch writes the custom
    order's challan (``DispatchOperations.sync_custom_dispatch_entry``).

    No stock is written: CONFIRMED to DISPATCHED moves the packets from reserved
    to consumed on its own.
    """
    from .DispatchOperations import (
        sync_custom_dispatch_entry,
        validated_loose_lot_numbers,
    )
    from .OrderOperations import assert_driver_details

    assert_order_kind(order, False, "dispatch")
    assert_custom_order_status(order, DISPATCHABLE_CUSTOM_ORDER_STATUS_CODES, "dispatch")

    # Validated before anything is written, so a bad lot number costs nothing.
    validated_loose_lot_numbers(order, lot_numbers)
    # Unconditional, unlike ``OrderOperations.dispatch_order``: a custom order is
    # always own-vehicle, so the driver and vehicle are never optional here even
    # though the shared request serializer allows them to be omitted.
    assert_driver_details(driver_name, driver_number, vehicle_number)

    dispatched_at = indian_now()
    to_city = order.delivery_address.city
    with recording(
        StockEventType.ORDER_DISPATCHED,
        StockEventDetail.FULL,
        custom_order_product_ids(order),
        source=order,
        actor=actor,
    ):
        assert_products_usable(
            custom_order_product_ids(order),
            field="status",
            action="be dispatched",
            subject="this custom order",
        )
        attach_private_dispatch_details(
            order,
            dispatched_by=actor,
            dispatch_date=dispatched_at.date(),
            from_city=from_city,
            to_city=to_city,
            driver_name=driver_name,
            driver_number=driver_number,
            vehicle_number=vehicle_number,
        )
        sync_custom_dispatch_entry(
            order,
            actor=actor,
            dispatched_at=dispatched_at,
            from_city=from_city,
            to_city=to_city,
            driver_name=driver_name,
            driver_number=driver_number,
            vehicle_number=vehicle_number,
            lot_numbers=lot_numbers,
        )
        update_custom_order_status(order, StatusIds.DISPATCHED)
    return order


def _assert_dispatched(order: CustomOrder, action: str) -> None:
    """Raise unless ``order`` is DISPATCHED -- the only status ``action`` applies to."""
    code = order.status.code if order.status_id else None
    if code != StatusIds.DISPATCHED.name:
        raise ValidationError(
            {
                "status": (
                    f"Cannot {action} a custom order that is {code}. "
                    f"Allowed: {StatusIds.DISPATCHED.name}."
                )
            }
        )


@transaction.atomic
def mark_delivered(order: CustomOrder, actual_delivery_date=None) -> CustomOrder:
    """Mark a dispatched custom order delivered (refused while a product on it is frozen)."""
    _assert_dispatched(order, "deliver")
    assert_products_usable(
        custom_order_product_ids(order),
        field="status",
        action="be delivered",
        subject="this custom order",
    )
    order.status = Status.by_id(StatusIds.DELIVERED)
    order.actual_delivery_date = actual_delivery_date or indian_now().date()
    order.full_clean()
    order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    return order


def revert_dispatch(order: CustomOrder) -> CustomOrder:
    """Reverse a dispatch, returning the custom order to ``CONFIRMED``.

    Its loose packets move back from consumed to reserved on their own -- both
    figures are derived from the status.

    The dispatch record and the challan stay attached, as for an order: they
    are what actually happened, a re-dispatch overwrites them, and the challan
    list leaves a non-dispatched order out by its status.

    Only today's dispatch can be reverted, the same rule an order follows --
    see ``OrderOperations.assert_dispatched_today``.
    """
    from .OrderOperations import assert_dispatched_today

    _assert_dispatched(order, "revert the dispatch of")
    assert_dispatched_today(order)
    with recording(
        StockEventType.DISPATCH_REVERTED,
        StockEventDetail.NONE,
        custom_order_product_ids(order),
        source=order,
    ):
        order.status = Status.by_id(StatusIds.CONFIRMED)
        order.actual_delivery_date = None
        order.full_clean()
        order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    return order


# -- Waste orders -----------------------------------------------------------
#
# A waste order is a custom order with ``made_from_waste`` set: its lines are
# kilograms of a product, drawn from that product's waste pool
# (``InventoryOperations.waste_available_kg``), at a per-kg price. It is born
# CONFIRMED like any custom order and only ever reaches DISPATCHED.
#
# These verbs deliberately do not run inside ``recording``: a waste order moves
# none of the stock-ledger figures (raw incoming/packed/wasted and the packet
# pools are all untouched -- the kg is already written off), so there is
# nothing to record. They take the product locks themselves instead.


def waste_requirements(items: Iterable[dict]) -> dict[Product, Decimal]:
    """Sum ``items``' kg per product; a product listed twice is refused."""
    needed: dict[Product, Decimal] = {}
    for item in items:
        product = item["product"]
        if product in needed:
            raise ValidationError(
                {"items": f"{product.name} is listed twice; use one line per product."}
            )
        needed[product] = Decimal(item["quantity_kg"])
    return needed


def assert_waste_covers(
    needed: Mapping[Product, Decimal],
    action: str = "create",
    *,
    held: Mapping[Product, Decimal] | None = None,
) -> None:
    """Raise unless each product's waste pool can supply ``needed`` kg.

    The waste counterpart of :func:`assert_loose_stock_covers`, with the same
    ``held`` contract: what the order already holds (its current lines, on an
    edit) is credited back, and a product whose need does not exceed it asks for
    nothing new, so shrinking an order is never refused. The pools are locked
    first and stay locked until the caller's transaction commits.
    """
    from . import InventoryOperations

    held = held or {}
    increases = {
        product: kg
        for product, kg in needed.items()
        if kg > held.get(product, Decimal("0"))
    }
    if not increases:
        return

    InventoryOperations.lock_waste_pools(product.id for product in increases)
    shortages = []
    for product, kg in increases.items():
        available = InventoryOperations.waste_available_kg(product) + held.get(
            product, Decimal("0")
        )
        if kg > available:
            shortages.append(f"{product.name}: need {kg} kg, have {available} kg")
    if shortages:
        raise ValidationError(
            {
                "quantity_kg": (
                    f"Not enough waste to {action} this waste order -- "
                    f"{'; '.join(shortages)}."
                )
            }
        )


@transaction.atomic
def create_waste_order(
    *,
    client: Client,
    delivery_address: Address,
    actor: User,
    items: Iterable[dict],
    special_comments: str = "",
    expected_delivery_date=None,
    booked_for: ClientChildOrg | None = None,
    hsn_code: str = "",
) -> CustomOrder:
    """Create a waste order and its kg lines atomically; it is born ``CONFIRMED``.

    ``hsn_code`` is an optional free-text HSN code kept on the order.

    Each entry in ``items`` is ``{"product", "quantity_kg", "negotiated_selling_price"}``
    (price per kg, required). Refused with a 400 -- and nothing written -- when
    any product's waste pool cannot cover its kilograms, summed over the order.
    """
    items = list(items)
    needed = waste_requirements(items)
    assert_products_usable(
        {product.pk for product in needed},
        field="items",
        action="be ordered",
        subject="this waste order",
    )
    assert_waste_covers(needed)

    order = CustomOrder(
        client=client,
        delivery_address=delivery_address,
        status=Status.by_id(StatusIds.CONFIRMED),
        created_by=actor,
        verified_by=actor,
        verified_at=indian_now(),
        special_comments=special_comments,
        booked_for=booked_for,
        made_from_waste=True,
        unit_of_measure=OrderUnit.KG,
        hsn_code=hsn_code,
    )
    if expected_delivery_date is not None:
        order.expected_delivery_date = expected_delivery_date
    order.full_clean()
    order.save()

    for item in items:
        add_waste_order_item(
            order,
            product=item["product"],
            quantity_kg=item["quantity_kg"],
            negotiated_selling_price=item["negotiated_selling_price"],
            actor=actor,
        )
    return order


def add_waste_order_item(
    order: CustomOrder,
    *,
    product: Product,
    quantity_kg,
    negotiated_selling_price,
    actor: User,
) -> CustomOrderItem:
    """Add a kg line to waste ``order``; the per-kg price is required."""
    item = CustomOrderItem(
        custom_order=order,
        product=product,
        packet_weight=None,
        packets=None,
        quantity_kg=quantity_kg,
        negotiated_selling_price=negotiated_selling_price,
        created_by=actor,
    )
    item.full_clean()
    item.save()
    return item


@transaction.atomic
def sync_waste_order_items(
    order: CustomOrder, items: list[dict], actor: User
) -> list[CustomOrderItem]:
    """Replace waste ``order``'s lines with ``items`` (full declarative replacement).

    The waste counterpart of :func:`sync_custom_order_items`: lines are matched
    by product (the natural key ``uniq_customorderitem_order_product_kg``), an
    existing line is updated in place, a soft-deleted one is restored rather than
    re-inserted, and one the caller omits is removed. A CONFIRMED order's lines
    are reserved waste, so raising a quantity or adding a product is re-checked
    against the pool with what the order already holds credited back.
    """
    assert_order_kind(order, True, "edit")
    if not items:
        raise ValidationError("A waste order must keep at least one item.")
    needed = waste_requirements(items)

    existing = {
        line.product_id: line
        for line in CustomOrderItem.all_objects.filter(custom_order=order).select_related(
            "product"
        )
    }

    assert_products_usable(
        {
            product.pk
            for product, kg in needed.items()
            if existing.get(product.pk) is None
            or existing[product.pk].is_deleted
            or kg > existing[product.pk].quantity_kg
        },
        field="items",
        action="have waste order lines added or raised",
        subject="this waste order",
    )

    if order.is_verified:
        held = {
            line.product: line.quantity_kg
            for line in existing.values()
            if not line.is_deleted
        }
        assert_waste_covers(needed, "edit", held=held)

    ordered: list[CustomOrderItem] = []
    for item in items:
        line = existing.pop(item["product"].pk, None)
        if line is None:
            line = add_waste_order_item(
                order,
                product=item["product"],
                quantity_kg=item["quantity_kg"],
                negotiated_selling_price=item["negotiated_selling_price"],
                actor=actor,
            )
        else:
            line.restore()
            line.quantity_kg = item["quantity_kg"]
            if item.get("negotiated_selling_price") is not None:
                line.negotiated_selling_price = item["negotiated_selling_price"]
            line.full_clean()
            line.save()
        ordered.append(line)

    for stale in existing.values():
        stale.mark_deleted(actor)

    return ordered


@transaction.atomic
def dispatch_waste_order(
    order: CustomOrder,
    *,
    actor: User,
    from_city: City,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
    lot_numbers: dict[str, str] | None = None,
) -> CustomOrder:
    """Record a dispatch against a CONFIRMED waste order and move it to DISPATCHED.

    The counterpart of :func:`dispatch_custom_order`: own vehicle only, today's
    date, the delivery address's city as the destination, and a challan
    (``DispatchOperations.sync_waste_dispatch_entry``). ``lot_numbers`` (keyed
    by product public id) is optional. No waste is written: CONFIRMED to
    DISPATCHED moves the kg from reserved to consumed on its own.
    """
    from . import InventoryOperations
    from .DispatchOperations import sync_waste_dispatch_entry, validated_waste_lot_numbers
    from .OrderOperations import assert_driver_details

    lot_numbers = lot_numbers or {}
    assert_order_kind(order, True, "dispatch")
    assert_custom_order_status(order, DISPATCHABLE_CUSTOM_ORDER_STATUS_CODES, "dispatch")
    validated_waste_lot_numbers(order, lot_numbers)
    assert_driver_details(driver_name, driver_number, vehicle_number)

    product_ids = custom_order_product_ids(order)
    InventoryOperations.lock_waste_pools(product_ids)
    assert_products_usable(
        product_ids,
        field="status",
        action="be dispatched",
        subject="this waste order",
    )

    dispatched_at = indian_now()
    to_city = order.delivery_address.city
    attach_private_dispatch_details(
        order,
        dispatched_by=actor,
        dispatch_date=dispatched_at.date(),
        from_city=from_city,
        to_city=to_city,
        driver_name=driver_name,
        driver_number=driver_number,
        vehicle_number=vehicle_number,
    )
    sync_waste_dispatch_entry(
        order,
        actor=actor,
        dispatched_at=dispatched_at,
        from_city=from_city,
        to_city=to_city,
        driver_name=driver_name,
        driver_number=driver_number,
        vehicle_number=vehicle_number,
        lot_numbers=lot_numbers,
    )
    update_custom_order_status(order, StatusIds.DISPATCHED)
    return order


# -- Admin edit / delete ----------------------------------------------------
#
# A custom order is born CONFIRMED, so that is the only status it can be
# corrected or withdrawn from. Once DISPATCHED or DELIVERED the packets have
# physically left, and rewriting or deleting the order would rewrite the loose
# stock history those dispatches are counted from.

EDITABLE_CUSTOM_ORDER_STATUS_CODES = frozenset({StatusIds.CONFIRMED.name})
DELETABLE_CUSTOM_ORDER_STATUS_CODES = frozenset({StatusIds.CONFIRMED.name})

CUSTOM_ORDER_CORE_FIELDS = (
    "delivery_address",
    "booked_for",
    "expected_delivery_date",
    "actual_delivery_date",
    "special_comments",
    "hsn_code",
)


def assert_custom_order_status(
    order: CustomOrder, allowed: frozenset[str], action: str
) -> None:
    """Guard an edit or delete on the custom order's current status.

    The custom-order counterpart of ``OrderOperations.assert_order_status``:
    raises ``ValidationError``, which the API turns into a 400.
    """
    code = order.status.code if order.status_id else None
    if code not in allowed:
        raise ValidationError(
            {
                "status": (
                    f"Cannot {action} a custom order that is {code}. "
                    f"Allowed: {', '.join(sorted(allowed))}."
                )
            }
        )


def update_custom_order_core(order: CustomOrder, **fields: object) -> CustomOrder:
    """Update the admin-editable core of a custom order.

    The same rules as ``OrderOperations.update_order_core``: ``client`` is not
    editable (the order belongs to the client it was booked for), neither is the
    audit record (``created_by`` / ``verified_by`` and their timestamps) nor the
    ``status``. An unknown field is a ``TypeError`` so such a call fails loudly.

    ``special_comments`` is **appended to**, never replaced -- see
    ``OrderOperations.appended_comment``.

    ``full_clean`` enforces that the delivery address belongs to the client.
    """
    from .OrderOperations import appended_comment

    unknown = set(fields) - set(CUSTOM_ORDER_CORE_FIELDS)
    if unknown:
        raise TypeError(
            f"Not an editable custom order field: {', '.join(sorted(unknown))}."
        )

    for field in CUSTOM_ORDER_CORE_FIELDS:
        if field not in fields:
            continue
        if field == "special_comments":
            order.special_comments = appended_comment(
                order.special_comments, str(fields[field])
            )
        else:
            setattr(order, field, fields[field])
    order.full_clean()
    order.save()
    return order


@transaction.atomic
def sync_custom_order_items(
    order: CustomOrder, items: list[dict], actor: User
) -> list[CustomOrderItem]:
    """Replace ``order``'s lines with ``items``, recording the stock it moves.

    See :func:`_sync_custom_order_items` for the rules. Editing a CONFIRMED
    custom order moves reserved loose packets, which the stock ledger records
    as ``ORDER_EDITED``.
    """
    assert_order_kind(order, False, "edit")
    products = {item["product"].pk for item in items if "product" in item}
    with recording(
        StockEventType.ORDER_EDITED,
        StockEventDetail.CUSTOM_ORDER_LINES_CHANGED,
        custom_order_product_ids(order, products),
        source=order,
        actor=actor,
    ):
        return _sync_custom_order_items(order, items, actor)


def _sync_custom_order_items(
    order: CustomOrder, items: list[dict], actor: User
) -> list[CustomOrderItem]:
    """Replace ``order``'s lines with ``items`` (full declarative replacement).

    Each entry is ``{"product", "packet_weight", "packets"}`` plus an optional
    ``"negotiated_selling_price"`` -- the same shape :func:`create_custom_order`
    takes. A pool not currently on the order is added, one already there is
    updated in place, and one the caller omits is removed. Lines are matched by
    ``(product, packet_weight)``: the natural key
    ``uniq_customorderitem_order_product_weight`` already enforces.

    Existing lines are looked up through ``all_objects`` because that unique
    constraint is **not** soft-delete aware: a pool taken off the order and
    later put back must have its original row restored, not a second inserted.

    **The lines are re-checked against loose stock** before anything is
    written: a CONFIRMED custom order's lines are reserved packets, so raising a
    count or adding a pool must be covered by what is available. The packets it
    already holds are credited back, and a line that shrinks or stays put asks
    for nothing new -- see :func:`assert_loose_stock_covers`.
    """
    if not items:
        raise ValidationError("A custom order must keep at least one item.")

    keys = [(item["product"].pk, item["packet_weight"]) for item in items]
    if len(set(keys)) != len(keys):
        raise ValidationError("The same product and packet weight is listed twice.")

    existing = {
        (line.product_id, line.packet_weight): line
        for line in CustomOrderItem.all_objects.filter(custom_order=order).select_related(
            "product"
        )
    }

    # A frozen product's line may be removed or lowered (that releases stock) but
    # not added back or raised. A soft-deleted line being restored counts as added.
    assert_products_usable(
        {
            item["product"].pk
            for item in items
            if existing.get((item["product"].pk, item["packet_weight"])) is None
            or existing[(item["product"].pk, item["packet_weight"])].is_deleted
            or item["packets"] > existing[(item["product"].pk, item["packet_weight"])].packets
        },
        field="items",
        action="have custom order lines added or raised",
        subject="this custom order",
    )

    if order.is_verified:
        held = loose_requirements(
            {
                "product": line.product,
                "packet_weight": line.packet_weight,
                "packets": line.packets,
            }
            for line in existing.values()
            if not line.is_deleted
        )
        assert_loose_stock_covers(loose_requirements(items), "edit", held=held)

    ordered: list[CustomOrderItem] = []
    for item in items:
        line = existing.pop((item["product"].pk, item["packet_weight"]), None)
        if line is None:
            line = add_custom_order_item(
                order,
                product=item["product"],
                packet_weight=item["packet_weight"],
                negotiated_selling_price=item.get("negotiated_selling_price"),
                packets=item["packets"],
                actor=actor,
            )
        else:
            line.restore()
            line.packets = item["packets"]
            if item.get("negotiated_selling_price") is not None:
                line.negotiated_selling_price = item["negotiated_selling_price"]
            line.full_clean()
            line.save()
        ordered.append(line)

    for stale in existing.values():
        stale.mark_deleted(actor)

    return ordered


@transaction.atomic
def delete_custom_order(order: CustomOrder, actor: User) -> None:
    """Withdraw a CONFIRMED custom order: reject it, then soft delete it and its lines.

    A stock-holding order may not be soft-deleted directly (see
    ``Order.refuse_deleting_stock_holder``) -- it must first leave the
    reserving status through its lifecycle. A custom order has no unverify or
    reject verb of its own, so withdrawing it *is* that step: it moves to
    REJECTED, which releases its reserved packets (reservations are derived
    from the status), and only then is it flagged deleted. The lines are
    flagged too, so nothing reading ``CustomOrderItem`` directly still sees
    them as live.
    """
    assert_custom_order_status(order, DELETABLE_CUSTOM_ORDER_STATUS_CODES, "delete")
    with recording(
        StockEventType.ORDER_RELEASED,
        StockEventDetail.CUSTOM_ORDER_WITHDRAWN,
        custom_order_product_ids(order),
        source=order,
        actor=actor,
    ):
        update_custom_order_status(order, StatusIds.REJECTED)
        for line in CustomOrderItem.objects.filter(custom_order=order):
            line.mark_deleted(actor)
        order.mark_deleted(actor)


def _hsn_payload(order: CustomOrder) -> dict:
    """``{"hsn_code": ...}`` for a waste order, nothing for a packet custom order.

    The HSN code belongs to waste orders only, so a packet order's responses do
    not carry the key at all.
    """
    return {"hsn_code": order.hsn_code} if order.made_from_waste else {}


def _weight_text(value) -> str | None:
    """A decimal as text, or None where the line has none (e.g. a kg line's packet weight)."""
    return None if value is None else str(value)


def custom_order_payload(order: CustomOrder) -> dict:
    """Frontend-facing dict for a custom order, keyed by public ids only."""
    return {
        "public_id": order.public_id,
        "client": {
            "company_name": order.client.company_name,
            "gst_number": order.client.gst_number,
        },
        "delivery_address": str(order.delivery_address),
        "status": order.status.code if order.status_id else None,
        "expected_delivery_date": order.expected_delivery_date.isoformat(),
        "actual_delivery_date": (
            order.actual_delivery_date.isoformat() if order.actual_delivery_date else None
        ),
        "special_comments": order.special_comments,
        "booked_for": child_org_payload(order.booked_for),
        "verified_at": order.verified_at.isoformat() if order.verified_at else None,
        "made_from_waste": order.made_from_waste,
        "unit_of_measure": order.unit_of_measure,
        **_hsn_payload(order),
        "total_amount": str(order.total_amount),
        "total_packets": order.total_packets,
        "total_kg": str(order.total_kg),
        "items": [
            {
                "product": {
                    "public_id": item.product.public_id,
                    "name": item.product.name,
                },
                "packet_weight": _weight_text(item.packet_weight),
                "negotiated_selling_price": str(item.negotiated_selling_price),
                "packets": item.packets,
                "quantity_kg": _weight_text(item.quantity_kg),
                "line_total": str(item.line_total),
            }
            for item in order.items.select_related("product").all()
        ],
    }


def custom_order_export_payload(order: CustomOrder) -> dict:
    """:func:`custom_order_payload` for the date-range export.

    Adds when the order was booked, the client's public id, and the city the
    order goes to (its own delivery address's city). Business fields only --
    no audit columns.
    """
    return {
        **custom_order_payload(order),
        "created_at": order.created_at.isoformat(),
        "client": client_summary_payload(order.client),
        "city": order_city_payload(order),
    }


def custom_order_list_payload(order: CustomOrder) -> dict:
    """Compact dict for the sales-admin custom-order list: one card per order.

    The custom-order counterpart of ``OrderOperations.order_list_payload``:
    what a list row shows (who, where, how much, what state), with one entry
    per line -- the product, the packet weight and how many packets.

    Reads the item rows off the instance, so a ``prefetch_related("items")``
    whose queryset ``select_related("product")`` keeps this query-free.
    """
    items = list(order.items.all())
    return {
        "public_id": order.public_id,
        "created_at": order.created_at.isoformat(),
        "status": order.status.code if order.status_id else None,
        "client": {
            "public_id": order.client.public_id,
            "company_name": order.client.company_name,
        },
        "delivery_address": str(order.delivery_address),
        "city": order_city_payload(order),
        "expected_delivery_date": order.expected_delivery_date.isoformat(),
        "booked_for": child_org_summary_payload(order.booked_for),
        "made_from_waste": order.made_from_waste,
        "unit_of_measure": order.unit_of_measure,
        **_hsn_payload(order),
        "total_amount": str(order.total_amount),
        "total_packets": order.total_packets,
        "total_kg": str(order.total_kg),
        "item_count": len(items),
        "items": [
            {
                "product": {
                    "public_id": item.product.public_id,
                    "name": item.product.name,
                    "image_url": item.product.image_url,
                },
                "packet_weight": _weight_text(item.packet_weight),
                "negotiated_selling_price": str(item.negotiated_selling_price),
                "packets": item.packets,
                "quantity_kg": _weight_text(item.quantity_kg),
            }
            for item in items
        ],
    }


def custom_order_detail_payload(order: CustomOrder) -> dict:
    """Full custom-order detail: :func:`custom_order_payload` with the client expanded.

    The same widening ``OrderOperations.order_detail_payload`` applies: the
    edit screen needs every client address *with its link id*, so the address
    picker can name one.
    """
    return {**custom_order_payload(order), "client": client_payload(order.client)}
