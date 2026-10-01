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

Everything here is derived or shape-only: nothing in this module writes rows.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Sum

from . import InventoryOperations
from .InventoryOperations import today
from .models import (
    InwardOtherMaterial,
    InwardRawMaterial,
    InwardRawMaterialStatus,
    OtherMaterialType,
    Product,
    Status,
    StatusIds,
)

if TYPE_CHECKING:
    from .models import OtherMaterialRecipe, Party


# Two-way status transitions for an ``InwardRawMaterial`` lot. Editing this dict
# is the **only** change needed to change the flips: every guard below re-reads
# it on each call. ``Lab Testing`` is the hub -- every route into or out of a
# dated status (``In Use``, ``Rejected``) passes through it, so ``In Use`` and
# ``Rejected`` never transition directly into one another; a lot already in
# use is reverted to ``Lab Testing`` first, which is where the packed-stock
# guard lives (see ``assert_raw_lot_removable``). Entering either dated status
# stamps ``effective_date`` with today; reverting either to ``Lab Testing``
# clears it (see ``UpdateInwardRawMaterialView``).
ALLOWED_RAW_STATUS_TRANSITIONS = {
    InwardRawMaterialStatus.LAB_TESTING: (
        InwardRawMaterialStatus.IN_USE,
        InwardRawMaterialStatus.RAW_MATERIAL_REJECTED,
    ),
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
    ``Rejected``) is always safe. A rejected lot was never packable in the
    first place, so leaving it is never refused. Removing a counted lot must
    not strand bags or sample packets that were packed from its kilograms
    with no raw material behind them.

    Raises ``ValueError`` with a message an API renders as a 400, the same
    convention as ``assert_raw_status_transition``.
    """
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


def party_payload(party: Party) -> dict:
    """Frontend-facing dict for one ``Party`` (lookup rows: id, not a key)."""
    return {
        "id": party.id,
        "name": party.name,
        "city": {"id": party.city_id, "name": party.city.name},
        "contact_number": party.contact_number,
    }


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


def inward_raw_material_payload(entry: InwardRawMaterial) -> dict:
    """Frontend-facing dict for one ``InwardRawMaterial`` lot (``IR-…``)."""
    return {
        "public_id": entry.public_id,
        "product": {
            "public_id": entry.product.public_id,
            "name": entry.product.name,
        },
        "party": {"id": entry.party_id, "name": entry.party.name},
        "lot_no": entry.lot_no,
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
        "party": {"id": entry.party_id, "name": entry.party.name},
        "quantity": str(entry.quantity),
        "effective_date": (
            entry.effective_date.isoformat() if entry.effective_date is not None else None
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
    -- a count has no "as of" of its own) and ``available_kg`` is what is left
    to pack; rejected kilograms are never counted there -- a rejected lot is
    invisible to the packing check regardless of its date. A product is
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
    products = Product.objects.in_bulk(product_ids)
    lines = []
    for product_id in product_ids:
        product = products[product_id]
        incoming_kg = incoming.get(product_id, {}).get("kg", Decimal("0.000"))
        rejected_kg = rejected.get(product_id, {}).get("kg", Decimal("0.000"))
        packed_kg = InventoryOperations.raw_bagged_kg(
            product
        ) + InventoryOperations.raw_loose_kg(product)
        row = incoming[product_id] if product_id in incoming else rejected[product_id]
        lines.append(
            {
                "product_id": product_id,
                "public_id": row["public_id"],
                "name": row["name"],
                "incoming_kg": incoming_kg,
                "packed_kg": packed_kg,
                "available_kg": incoming_kg - packed_kg,
                "rejected_kg": rejected_kg,
            }
        )
    lines.sort(key=lambda line: line["name"])
    return lines


def other_material_on_hand(
    as_of: date | None = None, *, material_type_ids: list[int] | None = None
) -> list[dict]:
    """Per-material-type on-hand position as of ``as_of`` (default today).

    ``on_hand`` is what has come in (entries with ``effective_date <= as_of``)
    minus what the packets currently packed have used, per the products'
    recipes -- see ``InventoryOperations.other_material_used``. The unit is the
    material type's own ``unit_type`` (count / kg / litre), so each line tells
    the reader how to read its ``on_hand`` number.

    Every material type that has come in or been used is listed, including
    one whose figure is zero or negative: a negative line means packets were
    counted that the recorded inward lots cannot cover, which is exactly what
    this report must not hide. ``material_type_ids`` narrows the report to
    those material types.
    """
    as_of = as_of or today()
    inward = InventoryOperations.other_material_inward(material_type_ids or None, as_of)
    used = InventoryOperations.other_material_used(material_type_ids or None)
    active = {
        material_type_id
        for figures in (inward, used)
        for material_type_id, amount in figures.items()
        if amount > 0
    }
    return [
        {
            "material_type_id": material_type.id,
            "name": material_type.name,
            "unit_type": material_type.unit_type,
            "on_hand": inward.get(material_type.id, Decimal("0"))
            - used.get(material_type.id, Decimal("0")),
        }
        for material_type in OtherMaterialType.all_objects.filter(
            id__in=active
        ).order_by("name")
    ]
