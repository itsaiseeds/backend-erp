"""Inward-movement operations for raw and other (packing) materials.

The two inward tables record *incoming lots*: a ``Party`` delivered a quantity
of raw material (``InwardRawMaterial``, kilograms) or of a packing material
(``InwardOtherMaterial``, in its material type's unit) for a product's recipe.
An entry is booked the day it arrives (``created_at``); an other-material entry
is stamped with ``effective_date`` = that same day, while a raw lot stamps one
on the day the user flips it to ``In Use``. Dates never backfill into
middleware the way the snapshot dates do -- a lot counts toward stock only once
its effective date has come, so nothing surprises the books mid-day.

Read-time derivation (no stored counters, no cron): the raw-material stock of a
product is the sum of its ``quantity_kg`` over lots with ``status=In Use`` and
``effective_date <= today``; the on-hand of a material type is the sum of its
``InwardOtherMaterial.quantity`` over entries with ``effective_date <= today``,
less what the packets currently packed have used per their recipes.
A freshly recorded other-material lot is therefore in stock the day it arrives;
a raw lot counts only while its status is ``In Use`` -- flipping stamps today,
reverting clears the date and drops it back out of stock.

Raw material is also **spent** by bag and loose-packet counts recorded in
``InventoryOperations`` -- a lot's kilograms are packed into bags or sample
packets there. ``assert_raw_lot_removable`` guards the two ways a lot can
leave the ``In Use`` pool (reverting to ``Lab Testing``, soft-deleting) so
neither can strand bags or packets that no longer have raw material behind
them.

Reads here are derived or shape-only. The lot **writes** at the bottom
(``create_raw_lot``, ``update_raw_lot``, ``create_other_lot``) live here so the
stock ledger wraps each exactly once, whichever API calls them.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, QuerySet, Sum
from django.http import Http404

from common.models import indian_now

from . import InventoryOperations
from .InventoryOperations import lock_raw_pools, today
from .models import (
    CustomOrderItem,
    InwardOtherMaterial,
    InwardRawMaterial,
    InwardRawMaterialStatus,
    OrderItem,
    OtherMaterialRecipe,
    OtherMaterialType,
    PartyType,
    Product,
    RawMaterialWaste,
    Status,
    StatusIds,
    StockEventDetail,
    StockEventType,
    StockPoolKind,
)
from .NotificationOperations import notify_lab_test_requested
from .ProductOperations import assert_products_usable
from .StockLedgerOperations import read_positions, recording

if TYPE_CHECKING:
    from authentication.models import User

    from .models import OtherMaterialRecipe, Party


# Status transitions an **admin** may request on an ``InwardRawMaterial`` lot
# through the status PATCH: only a *revert* back to ``Lab Testing``. Leaving
# ``Lab Testing`` -- to ``In Use`` (Pass) or ``Rejected`` (Fail) -- is the lab
# tester's decision alone and goes through ``LabTestingOperations``, which
# does not consult this table. Editing this dict is the only change needed to
# change what the PATCH accepts: every guard below re-reads it on each call.
# ``Lab Testing`` is the hub -- ``In Use`` and ``Rejected`` never transition
# directly into one another; a lot already in use is reverted to ``Lab
# Testing`` first, which is where the packed-stock guard lives (see
# ``assert_raw_lot_removable``). Entering either dated status stamps
# ``effective_date`` with today; reverting either to ``Lab Testing`` clears it
# (see ``UpdateInwardRawMaterialSerializer``).
ALLOWED_RAW_STATUS_TRANSITIONS = {
    InwardRawMaterialStatus.IN_USE: (InwardRawMaterialStatus.LAB_TESTING,),
    InwardRawMaterialStatus.RAW_MATERIAL_REJECTED: (InwardRawMaterialStatus.LAB_TESTING,),
}

# The two statuses in which a lot carries an effective date -- "usable from"
# for In Use, "disposable from" for Rejected. Lab Testing carries none.
DATED_RAW_STATUSES = (
    InwardRawMaterialStatus.IN_USE,
    InwardRawMaterialStatus.RAW_MATERIAL_REJECTED,
)


def assert_raw_status_transition(current, requested) -> None:
    """Raise unless ``requested`` continues ``current`` along its allowed path.

    Raises ``ValueError`` with a message an API renders as a 400, so callers
    (serializers/views) never decide what a legal move is -- this table owns it.
    """
    allowed = ALLOWED_RAW_STATUS_TRANSITIONS.get(current, ())
    if requested not in allowed:
        current_label = InwardRawMaterialStatus(current).label
        requested_label = InwardRawMaterialStatus(requested).label
        if current == InwardRawMaterialStatus.LAB_TESTING:
            raise ValueError(
                "Only a lab tester can move a lot out of Lab Testing: "
                "a Pass makes it In Use and a Fail makes it Rejected."
            )
        if not allowed:
            raise ValueError(
                f"'{requested_label}' is not a valid transition from "
                f"the {current_label} status."
            )
        raise ValueError(
            f"'{current_label}' can only move to "
            f"{', '.join(InwardRawMaterialStatus(code).label for code in allowed)}."
        )


def raw_status_of(entry: InwardRawMaterial) -> InwardRawMaterialStatus:
    """The display status of ``entry``'s current ``Status`` row."""
    return InwardRawMaterialStatus[entry.status.code]


def status_row_for(choice: InwardRawMaterialStatus) -> Status:
    """The seeded ``Status`` row a display choice resolves to."""
    return Status.objects.get(code=choice.name)


def assert_raw_lot_removable(entry: InwardRawMaterial) -> None:
    """Raise unless ``entry`` may leave the in-use raw pool (revert or delete).

    Only a lot that is currently ``In Use`` *and* whose ``effective_date`` has
    come is counted in ``InventoryOperations.raw_available_kg`` at all --
    removing anything else (still ``Lab Testing``, dated in the future, or
    ``Rejected``) is always safe -- except that a rejected lot with kg on a
    rejected order cannot leave Rejected. A rejected lot was never packable in
    the first place, so nothing else refuses it. Removing a counted lot must
    not strand bags or sample packets that were packed from its kilograms
    with no raw material behind them.

    Raises ``ValueError`` with a message an API renders as a 400, the same
    convention as ``assert_raw_status_transition``.
    """
    if raw_status_of(entry) == InwardRawMaterialStatus.RAW_MATERIAL_REJECTED:
        try:
            InventoryOperations.assert_rejected_lot_not_booked(entry, "remove this lot")
        except ValidationError as exc:
            raise ValueError(exc.messages[0]) from None
        return
    is_counted = (
        raw_status_of(entry) == InwardRawMaterialStatus.IN_USE
        and entry.effective_date is not None
        and entry.effective_date <= InventoryOperations.today()
    )
    if not is_counted:
        return
    remaining = InventoryOperations.raw_available_kg(entry.product) - entry.quantity_kg
    if remaining < 0:
        raise ValueError(
            f"{-remaining} kg of this lot is already packed into bags or "
            "sample packets and cannot be removed."
        )


# -- Payloads ------------------------------------------------------------------


def other_material_stock_payload(
    material_type_ids: list[int] | None = None, *, by_configuration: bool = False
) -> dict:
    """The other-material on-hand position as ``{"as_of", "lines"}``.

    Shared by the sales-admin view and both Android versions. Grouped by
    ``(product, packet_weight, material type)`` when ``by_configuration``, each
    line then carrying ``product`` and ``packet_weight``; otherwise one line per
    material type.
    """
    as_of = today()
    lines = (
        other_material_on_hand_by_configuration(as_of, material_type_ids=material_type_ids)
        if by_configuration
        else other_material_on_hand(as_of, material_type_ids=material_type_ids)
    )
    return {
        "as_of": as_of.isoformat(),
        "lines": [
            {
                **(
                    {
                        "product": {
                            "public_id": line["product_public_id"],
                            "name": line["product_name"],
                        },
                        "packet_weight": str(line["packet_weight"]),
                    }
                    if by_configuration
                    else {}
                ),
                "material_type": {
                    "id": line["material_type_id"],
                    "name": line["name"],
                    "unit_type": line["unit_type"],
                },
                "on_hand": str(line["on_hand"]),
            }
            for line in lines
        ],
    }


def party_payload(party: Party) -> dict:
    """Frontend-facing dict for one ``Party`` (lookup rows: id, not a key)."""
    return {
        "id": party.id,
        "name": party.name,
        "city": {"id": party.city_id, "name": party.city.name},
        "party_type": party.party_type,
        "contact_number": party.contact_number,
    }


def party_type_options() -> list[dict]:
    """Every ``PartyType`` as ``{value, label}``, for pickers and filters."""
    return [{"value": choice.value, "label": choice.label} for choice in PartyType]


def assert_party_type(party: Party, expected: PartyType) -> None:
    """Raise unless ``party`` supplies ``expected`` material.

    A raw-material lot may only be booked against a ``RAW_MATERIAL`` party and
    an other-material lot only against an ``OTHER_MATERIAL`` one. Raises
    ``ValueError`` with a message an API renders as a 400.
    """
    if party.party_type != expected:
        raise ValueError(
            f"Party '{party.name}' is of type {PartyType(party.party_type).label}; "
            f"this booking needs a party of type {PartyType(expected).label}."
        )


def other_material_type_payload(material_type: OtherMaterialType) -> dict:
    """Frontend-facing dict for one ``OtherMaterialType`` (lookup row)."""
    return {
        "id": material_type.id,
        "name": material_type.name,
        "unit_type": material_type.unit_type,
    }


def recipe_payload(recipe: OtherMaterialRecipe) -> dict:
    """Frontend-facing dict for one ``OtherMaterialRecipe`` (``OMR-…``)."""
    material_type = recipe.material_type
    return {
        "public_id": recipe.public_id,
        "product": {
            "public_id": recipe.product.public_id,
            "name": recipe.product.name,
        },
        "material_type": {
            "id": material_type.id,
            "name": material_type.name,
            "unit_type": material_type.unit_type,
        },
        "packet_weight": str(recipe.packet_weight),
        "quantity": str(recipe.quantity),
    }


def _party_ref(entry: InwardRawMaterial | InwardOtherMaterial) -> dict:
    """The ``party`` block of a lot payload.

    A lot an accepted return booked has no party: it reads
    ``{"id": null, "name": "Return Order (<ORD-…>)"}`` so the list still shows
    where the stock came from.
    """
    ret = entry.return_order
    if ret is not None:
        return {"id": None, "name": f"Return Order ({ret.order.public_id})"}
    party = entry.party
    return {"id": entry.party_id, "name": party.name if party is not None else ""}


def _return_order_ref(entry: InwardRawMaterial | InwardOtherMaterial) -> dict | None:
    """The ``return_order`` block of a lot payload; null for an ordinary lot."""
    ret = entry.return_order
    if ret is None:
        return None
    return {"public_id": ret.public_id, "order_public_id": ret.order.public_id}


def inward_raw_material_payload(entry: InwardRawMaterial) -> dict:
    """Frontend-facing dict for one ``InwardRawMaterial`` lot (``IR-…``)."""
    return {
        "public_id": entry.public_id,
        "product": {
            "public_id": entry.product.public_id,
            "name": entry.product.name,
        },
        "party": _party_ref(entry),
        "return_order": _return_order_ref(entry),
        "lot_no": entry.lot_no,
        "farmer_name": entry.farmer_name,
        "quantity_kg": str(entry.quantity_kg),
        "status": raw_status_of(entry).value,
        "lab_sampling_date": (
            entry.lab_sampling_date.isoformat()
            if entry.lab_sampling_date is not None
            else None
        ),
        "effective_date": (
            entry.effective_date.isoformat() if entry.effective_date is not None else None
        ),
        "lab_testing": lab_testing_ref(entry),
        "created_by": (
            {"id": entry.created_by_id, "name": entry.created_by.display_name}
            if entry.created_by_id is not None
            else None
        ),
    }


def lab_testing_ref(entry: InwardRawMaterial) -> dict | None:
    """The ``lab_testing`` block of a lot payload; null until the lot is tested.

    A lot waiting for a re-test keeps its record, with ``result`` null.
    """
    test = entry.lab_testing
    if test is None:
        return None
    return {
        "public_id": test.public_id,
        "result": test.result,
        "grow_out_test": str(test.grow_out_test),
    }


def raw_waste_payload(entry: RawMaterialWaste) -> dict:
    """Frontend-facing dict for one ``RawMaterialWaste`` row (``WS-…``)."""
    return {
        "public_id": entry.public_id,
        "product": {
            "public_id": entry.product.public_id,
            "name": entry.product.name,
        },
        "quantity_kg": str(entry.quantity_kg),
        "reason": entry.reason,
        "created_at": entry.created_at.isoformat(),
        "created_by": (
            {"id": entry.created_by_id, "name": entry.created_by.display_name}
            if entry.created_by_id is not None
            else None
        ),
    }


def inward_other_material_payload(entry: InwardOtherMaterial) -> dict:
    """Frontend-facing dict for one ``InwardOtherMaterial`` lot (``IO-…``)."""
    recipe = entry.recipe
    material_type = recipe.material_type
    return {
        "public_id": entry.public_id,
        "recipe": {
            "public_id": recipe.public_id,
            "material_type": {
                "id": material_type.id,
                "name": material_type.name,
            },
            "product": {
                "public_id": recipe.product.public_id,
                "name": recipe.product.name,
            },
            "packet_weight": str(recipe.packet_weight),
        },
        "party": _party_ref(entry),
        "return_order": _return_order_ref(entry),
        "quantity": str(entry.quantity),
        "effective_date": (
            entry.effective_date.isoformat() if entry.effective_date is not None else None
        ),
        "created_by": (
            {"id": entry.created_by_id, "name": entry.created_by.display_name}
            if entry.created_by_id is not None
            else None
        ),
    }


# -- Read-time stock aggregates ------------------------------------------------


def _dated_raw_kg_by_product(
    status_id: int, as_of: date, product_public_ids: list[str] | None
) -> dict[int, dict]:
    """``{product_id: {public_id, name, kg}}`` for dated, reached, live lots of
    one ``status_id``, summed over ``quantity_kg``. Rows summing to zero or
    less are dropped (nothing left to report)."""
    query = InwardRawMaterial.objects.filter(
        effective_date__isnull=False,
        effective_date__lte=as_of,
        status_id=status_id,
    )
    if product_public_ids:
        query = query.filter(product__public_id__in=product_public_ids)
    rows = (
        query.values("product_id", "product__public_id", "product__name")
        .annotate(kg=Sum("quantity_kg"))
        .filter(kg__gt=0)
    )
    return {
        row["product_id"]: {
            "public_id": row["product__public_id"],
            "name": row["product__name"],
            "kg": row["kg"],
        }
        for row in rows
    }


def raw_incoming_stock(
    as_of: date | None = None, *, product_public_ids: list[str] | None = None
) -> list[dict]:
    """Per-product incoming raw-material position as of ``as_of`` (default today).

    Only lots with ``status=In Use`` and ``effective_date <= as_of`` count
    toward ``incoming_kg``; only ``status=Rejected`` lots, dated and reached
    the same way, count toward ``rejected_kg``. ``packed_kg`` is what has
    since been packed into bags or sample packets
    (``InventoryOperations.raw_bagged_kg`` + ``raw_loose_kg``, read as of now
    -- a count has no "as of" of its own), ``wasted_kg`` is what was written
    off (``raw_wasted_kg``, undated) and ``available_kg`` is what is left to
    pack. The ``waste_*_kg`` figures are the waste pool waste orders draw on
    (``InventoryOperations.waste_available_kg``): they do not change
    ``available_kg``, since waste is already written off from raw. Rejected
    kilograms are never counted there -- a rejected lot is
    invisible to the packing check regardless of its date. ``rejected_kg`` is
    net of what rejected orders have sold (display only; the stock ledger keeps
    the whole lot total). A product is
    listed whenever it has incoming or rejected kilograms, so a product whose
    entire intake was rejected still appears. The list is ready for display:
    each entry carries the product's public id / name and Decimal kilogram
    figures (serializers turn them into strings). ``product_public_ids``
    narrows the report to those products.
    """
    as_of = as_of or today()
    incoming = _dated_raw_kg_by_product(StatusIds.IN_USE.value, as_of, product_public_ids)
    rejected = _dated_raw_kg_by_product(
        StatusIds.RAW_MATERIAL_REJECTED.value, as_of, product_public_ids
    )
    product_ids = sorted(set(incoming) | set(rejected))
    sold = InventoryOperations.rejected_sold_kg_by_product(product_ids)
    products = Product.objects.in_bulk(product_ids)
    lines = []
    for product_id in product_ids:
        product = products[product_id]
        incoming_kg = incoming.get(product_id, {}).get("kg", Decimal("0.000"))
        # Rejected kg already sold on a rejected order is no longer in stock.
        rejected_kg = rejected.get(product_id, {}).get("kg", Decimal("0.000")) - sold.get(
            product_id, Decimal("0.000")
        )
        packed_kg = InventoryOperations.raw_bagged_kg(
            product
        ) + InventoryOperations.raw_loose_kg(product)
        wasted_kg = InventoryOperations.raw_wasted_kg(product)
        row = incoming[product_id] if product_id in incoming else rejected[product_id]
        lines.append(
            {
                "product_id": product_id,
                "public_id": row["public_id"],
                "name": row["name"],
                "is_usable": product.is_usable,
                "incoming_kg": incoming_kg,
                "packed_kg": packed_kg,
                "wasted_kg": wasted_kg,
                "available_kg": incoming_kg - packed_kg - wasted_kg,
                "rejected_kg": rejected_kg,
                "waste_reserved_kg": InventoryOperations.waste_reserved_kg(product),
                "waste_consumed_kg": InventoryOperations.waste_consumed_kg(product),
                "waste_available_kg": InventoryOperations.waste_available_kg(product),
            }
        )
    lines.sort(key=lambda line: line["name"])
    return lines


def other_material_on_hand(
    as_of: date | None = None, *, material_type_ids: list[int] | None = None
) -> list[dict]:
    """Per-material-type on-hand position as of ``as_of`` (default today).

    ``on_hand`` is the sum of the type's configuration balances: what has come in
    (entries with ``effective_date <= as_of``) minus what the packets currently
    packed have used -- see ``InventoryOperations.other_material_used``. The unit
    is the material type's own ``unit_type`` (count / kg / litre), so each line
    tells the reader how to read its ``on_hand`` number.

    Every material type that has come in or been used is listed, including
    one whose figure is zero or negative: a negative line means packets were
    counted that the recorded inward lots cannot cover, which is exactly what
    this report must not hide. ``material_type_ids`` narrows the report to
    those material types.
    """
    as_of = as_of or today()
    inward = InventoryOperations.other_material_inward(
        as_of=as_of, material_type_ids=material_type_ids or None
    )
    used = InventoryOperations.other_material_used(
        material_type_ids=material_type_ids or None
    )
    zero = Decimal("0")
    on_hand: dict[int, Decimal] = {}
    active: set[int] = set()
    for figures, sign in ((inward, 1), (used, -1)):
        for (_, _, material_type_id), amount in figures.items():
            on_hand[material_type_id] = on_hand.get(material_type_id, zero) + sign * amount
            if amount > 0:
                active.add(material_type_id)
    return [
        {
            "material_type_id": material_type.id,
            "name": material_type.name,
            "unit_type": material_type.unit_type,
            "on_hand": on_hand.get(material_type.id, zero),
        }
        for material_type in OtherMaterialType.all_objects.filter(
            id__in=active
        ).order_by("name")
    ]


def other_material_on_hand_by_configuration(
    as_of: date | None = None, *, material_type_ids: list[int] | None = None
) -> list[dict]:
    """Packing-material position per ``(product, packet weight, material type)``.

    Stock received for one product/weight is not presented as stock for another
    product/weight: this is the same keyed figure the guards enforce.

    ``on_hand`` is the configuration's reached inward quantity less the material
    used by packets packed under its recipes.  A live recipe with no movement is
    included as a zero balance so the stock screen still exposes every current
    product configuration.
    """
    as_of = as_of or today()
    zero = Decimal("0.000")
    incoming = InventoryOperations.other_material_inward(
        as_of=as_of, material_type_ids=material_type_ids
    )
    used = InventoryOperations.other_material_used(material_type_ids=material_type_ids)

    recipe_filter = Q()
    if material_type_ids is not None:
        recipe_filter = Q(material_type_id__in=material_type_ids)
    keys = set(incoming) | set(used) | {
        (recipe.product_id, Decimal(recipe.packet_weight), recipe.material_type_id)
        for recipe in OtherMaterialRecipe.objects.filter(recipe_filter)
    }
    products = Product.all_objects.in_bulk(key[0] for key in keys)
    materials = OtherMaterialType.all_objects.in_bulk(key[2] for key in keys)
    rows = []
    for key in keys:
        product_id, packet_weight, material_type_id = key
        product = products[product_id]
        material = materials[material_type_id]
        rows.append(
            {
                "product_public_id": product.public_id,
                "product_name": product.name,
                "packet_weight": packet_weight,
                "material_type_id": material_type_id,
                "name": material.name,
                "unit_type": material.unit_type,
                "on_hand": incoming.get(key, zero) - used.get(key, zero),
            }
        )
    return sorted(rows, key=lambda row: (row["product_name"], row["packet_weight"], row["name"]))


def locked_raw_lot(queryset: QuerySet, public_id: str) -> InwardRawMaterial:
    """Load a lot with its product's raw pool locked, for a revert or delete.

    Removing a lot is checked against the raw pool (``assert_raw_lot_removable``)
    and stock counts are written against that same pool under
    ``lock_raw_pools``. Taking the same lock here, *before* the lot is read,
    stops a count and a removal from interleaving and stranding bags with no
    raw material behind them. The lot itself is then read -- and locked --
    after the pool, so its status is the one the check will act on and every
    caller acquires the rows in the same order.

    The lot's own lock is taken on the bare row and the joined load runs
    afterwards: a locking query that waited re-checks its joins against the
    changed row, so locking through the ``status`` join would drop a lot whose
    status had just changed and 404 (see ``GetOrderView.get_locked_order``).

    Must be called inside ``transaction.atomic``.
    """
    lots = InwardRawMaterial.objects.filter(public_id=public_id)
    product_id = lots.values_list("product_id", flat=True).first()
    if product_id is None:
        raise Http404("No InwardRawMaterial matches the given query.")
    lock_raw_pools([product_id])
    # Soft-deleted by a request that held the lock before us: gone, so a 404.
    pk = lots.select_for_update().values_list("pk", flat=True).first()
    if pk is None:
        raise Http404("No InwardRawMaterial matches the given query.")
    return queryset.get(pk=pk)


# -- Lot writes (recorded in the stock ledger) --------------------------------

_RAW_STATUS_DETAILS = {
    InwardRawMaterialStatus.IN_USE: StockEventDetail.RAW_LOT_IN_USE,
    InwardRawMaterialStatus.RAW_MATERIAL_REJECTED: StockEventDetail.RAW_LOT_REJECTED,
    InwardRawMaterialStatus.LAB_TESTING: StockEventDetail.RAW_LOT_BACK_TO_LAB,
}


def raw_status_detail(entry: InwardRawMaterial) -> StockEventDetail:
    """The ledger detail for a lot that ended up in its current status."""
    return _RAW_STATUS_DETAILS[raw_status_of(entry)]


def assert_can_change_inward(actor: User | None) -> None:
    """Raise unless ``actor`` may book, change or delete inward raw / other material.

    The same gate as writing a stock count: a superuser, or an admin holding
    ``Admin.can_update_stock_count``. Called by the sales-admin inward write views;
    viewing the lists only needs an admin, and the godown manager's own Android
    endpoints are not gated by it.
    """
    if actor is None:
        raise PermissionDenied("A user must be provided to change inward material.")
    if getattr(actor, "is_superuser", False):
        return
    admin = getattr(actor, "live_admin_profile", None)
    if admin is None or not admin.can_update_stock_count:
        raise PermissionDenied(
            f"User '{actor}' is not allowed to change inward material "
            "(requires permission to update the stock count)."
        )


def create_raw_lot(
    *,
    product: Product,
    party: Party,
    lot_no: str,
    farmer_name: str,
    quantity_kg: Decimal,
    lab_sampling_date: date,
    actor: User,
) -> InwardRawMaterial:
    """Book a raw-material lot. It starts in Lab Testing, so it moves no stock yet."""
    with recording(
        StockEventType.INWARD_OPERATIONS,
        StockEventDetail.RAW_LOT_IN_USE,
        [product.id],
        actor=actor,
    ) as rec:
        assert_products_usable([product], action="receive an inward lot")
        entry = InwardRawMaterial.objects.create(
            product=product,
            party=party,
            lot_no=lot_no,
            farmer_name=farmer_name,
            quantity_kg=quantity_kg,
            lab_sampling_date=lab_sampling_date,
            created_by=actor,
        )
        rec.source = entry
    notify_lab_test_requested(entry, actor=actor)
    return entry


def update_raw_lot(
    entry: InwardRawMaterial, values: Mapping[str, object], actor: User
) -> InwardRawMaterial:
    """Apply a lot's lifecycle update (dates and status), recording what it moves.

    Call inside ``transaction.atomic`` with the lot loaded through
    :func:`locked_raw_lot`. The event's detail is the status the lot ends in.

    A lot an accepted return booked is refused (400): only reverting that
    return's accept moves it.

    Sending a lot back to ``Lab Testing`` empties its lab test's ``result`` --
    the inputs stay for the lab tester to correct -- and asks every lab tester
    to test it again.
    """
    entry.refuse_return_lot_change()
    previous = raw_status_of(entry)
    with recording(
        StockEventType.INWARD_OPERATIONS,
        StockEventDetail.RAW_LOT_IN_USE,
        [entry.product_id],
        source=entry,
        actor=actor,
    ) as rec:
        assert_products_usable(
            [entry.product_id], field="status", action="have its inward lot changed"
        )
        for field in ("lab_sampling_date", "effective_date", "status", "lab_testing"):
            if field in values:
                setattr(entry, field, values[field])
        entry.save()
        rec.detail = raw_status_detail(entry)
        sent_back = (
            previous != InwardRawMaterialStatus.LAB_TESTING
            and raw_status_of(entry) == InwardRawMaterialStatus.LAB_TESTING
        )
        test = entry.lab_testing
        if sent_back and test is not None and test.result is not None:
            test.result = None
            test.save(update_fields=["result", "updated_at"])
    if sent_back:
        notify_lab_test_requested(entry, actor=actor)
    return entry


def create_other_lot(
    *, party: Party, recipe: OtherMaterialRecipe, quantity: Decimal, actor: User
) -> InwardOtherMaterial:
    """Book an other-material lot; it is in stock the day it arrives.

    Refused (``ValidationError``, a 400 -- and the booking rolls back) when the
    lot's own configuration -- product, packet weight and material type -- still
    falls short of what the bags and packets already packed use: bags exist that
    the inward lots do not cover, so the lot must at least make up that gap.
    """
    with recording(
        StockEventType.INWARD_OPERATIONS,
        StockEventDetail.OTHER_MATERIAL_RECEIVED,
        [recipe.product_id],
        actor=actor,
    ) as rec:
        assert_products_usable([recipe.product_id], field="recipe", action="receive an inward lot")
        entry = InwardOtherMaterial.objects.create(
            party=party,
            recipe=recipe,
            quantity=quantity,
            effective_date=today(),
            created_by=actor,
        )
        # recording() already locked the recipe's material type, so this read is stable.
        key = (recipe.product_id, Decimal(recipe.packet_weight), recipe.material_type_id)
        available = InventoryOperations.other_material_available([key])[key]
        if available < 0:
            material_type = recipe.material_type
            raise ValidationError(
                f"Not enough inward material for existing bags: "
                f"'{material_type.name}' for '{recipe.product.name}' "
                f"{Decimal(recipe.packet_weight):.3f}kg is still short by "
                f"{-available} {material_type.unit_type} for the bags already packed."
            )
        rec.source = entry
    return entry


# -- Product-to-product transfer -----------------------------------------------

# Order statuses in which an order still has a claim on its products: it may be
# booked, under review, confirmed (bags reserved) or on hold. A dispatched,
# delivered or rejected order is finished with them.
OPEN_ORDER_STATUS_IDS = (
    StatusIds.BOOKED,
    StatusIds.UNDER_REVIEW,
    StatusIds.CONFIRMED,
    StatusIds.ON_HOLD,
)


def _idle_problems(product: Product) -> list[str]:
    """Why ``product`` is still holding bags, packets or orders; empty when idle.

    Read with the same figures the stock screens and the ledger use
    (:func:`StockLedgerOperations.read_positions`): counted bags and loose
    packets, and what orders have reserved. Open order lines are checked on top,
    because an order still being reviewed reserves nothing yet but is about to.
    """
    position = read_positions([product.id])[product.id]
    counted = {StockPoolKind.BAG: 0, StockPoolKind.LOOSE: 0}
    reserved = {StockPoolKind.BAG: 0, StockPoolKind.LOOSE: 0}
    for (kind, _), figures in position.items():
        if kind in counted:
            counted[kind] += int(figures["on_hand"])
            reserved[kind] += int(figures["reserved"])
    problems = []
    if counted[StockPoolKind.BAG]:
        problems.append(f"{counted[StockPoolKind.BAG]} bag(s) in stock")
    if counted[StockPoolKind.LOOSE]:
        problems.append(f"{counted[StockPoolKind.LOOSE]} loose packet(s) in stock")
    if reserved[StockPoolKind.BAG] or reserved[StockPoolKind.LOOSE]:
        problems.append("bags or packets reserved for orders")
    if (
        OrderItem.objects.filter(
            product_packaging__product=product,
            order__is_deleted=False,
            order__status_id__in=OPEN_ORDER_STATUS_IDS,
        ).exists()
        or CustomOrderItem.objects.filter(
            product=product,
            custom_order__is_deleted=False,
            custom_order__status_id__in=OPEN_ORDER_STATUS_IDS,
        ).exists()
    ):
        problems.append("open orders")
    return problems


def transfer_raw_material(
    *, source: Product, target: Product, quantity_kg: Decimal, actor: User
) -> list[InwardRawMaterial]:
    """Move ``quantity_kg`` of ``source``'s inward raw material to ``target``.

    For a product bought under the wrong name or left over from a cancelled
    plan: the kilograms are not wasted but re-homed. Stock is derived from
    ``In Use`` lots, so the move is made on the lots themselves -- the
    source's oldest counted lots are reduced (a lot emptied is soft-deleted)
    and each reduction is re-booked as a new ``In Use`` lot of ``target``,
    effective today, copying the party, supplier lot number and sampling date.
    The new lot's ``farmer_name`` says where it came from, and it has no lab
    test of its own. A lot booked by an accepted return is never touched: only
    reverting that return may change it.

    Refused (400, ``ValidationError`` keyed by field) unless:

    * the two products differ and share a crop;
    * both are usable;
    * ``source`` is idle -- no bag or loose packet in stock or reserved and no
      open order line (see :func:`_idle_problems`);
    * ``source`` has ``quantity_kg`` of unpacked raw material to give, in
      lots that are movable.

    Recorded in the stock ledger as ``RAW_LOT_TRANSFERRED``, one event per
    product. Returns the new ``target`` lots, oldest source lot first.
    """
    if source.pk == target.pk:
        raise ValidationError({"target_product": "Source and target must be different products."})
    if source.crop_id != target.crop_id:
        raise ValidationError(
            {
                "target_product": (
                    f"'{source.name}' is a {source.crop.name} product and "
                    f"'{target.name}' a {target.crop.name} one: "
                    "a transfer must stay within one crop."
                )
            }
        )
    with recording(
        StockEventType.INWARD_OPERATIONS,
        StockEventDetail.RAW_LOT_TRANSFERRED,
        [source.id, target.id],
        actor=actor,
    ) as rec:
        assert_products_usable([source, target], action="take part in a transfer")
        lock_raw_pools([source.id, target.id])
        problems = _idle_problems(source)
        if problems:
            raise ValidationError(
                {
                    "source_product": (
                        f"'{source.name}' cannot be transferred while it has "
                        f"{', '.join(problems)}."
                    )
                }
            )
        available = InventoryOperations.raw_available_kg(source)
        if quantity_kg > available:
            raise ValidationError(
                {
                    "quantity_kg": (
                        f"Not enough raw material in '{source.name}': "
                        f"{max(available, Decimal('0'))} kg available, {quantity_kg} kg requested."
                    )
                }
            )
        lots = list(
            InwardRawMaterial.objects.select_for_update(of=("self",))
            .select_related("party")
            .filter(
                product=source,
                status_id=StatusIds.IN_USE.value,
                effective_date__isnull=False,
                effective_date__lte=today(),
                return_order__isnull=True,
            )
            .order_by("effective_date", "pk")
        )
        movable = sum((lot.quantity_kg for lot in lots), Decimal("0"))
        if quantity_kg > movable:
            raise ValidationError(
                {
                    "quantity_kg": (
                        f"Only {movable} kg of '{source.name}' can be moved: the rest "
                        "came back on a return order and stays with that return."
                    )
                }
            )

        moved: list[InwardRawMaterial] = []
        touched: list[InwardRawMaterial] = []
        remaining = quantity_kg
        for lot in lots:
            if remaining <= 0:
                break
            take = min(lot.quantity_kg, remaining)
            moved.append(
                InwardRawMaterial.objects.create(
                    product=target,
                    party=lot.party,
                    lot_no=lot.lot_no,
                    farmer_name=f"{lot.farmer_name} (transferred from {source.name})"[:255],
                    quantity_kg=take,
                    lab_sampling_date=lot.lab_sampling_date,
                    status_id=StatusIds.IN_USE.value,
                    effective_date=today(),
                    created_by=actor,
                )
            )
            lot.quantity_kg -= take
            fields = ["quantity_kg", "updated_at"]
            if lot.quantity_kg == 0:
                # Emptied: retire it directly (as ``ProductOperations`` does for a
                # description bullet) -- the soft-delete guard would re-enter the
                # ledger recording this transfer already holds.
                lot.is_deleted = True
                lot.deleted_at = indian_now()
                lot.deleted_by = actor
                fields += ["is_deleted", "deleted_at", "deleted_by"]
            lot.save(update_fields=fields)
            touched.append(lot)
            remaining -= take
        rec.sources = {source.id: touched[0], target.id: moved[0]}
    return moved
