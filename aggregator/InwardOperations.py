"""Inward-movement operations for raw and other (packing) materials.

The two inward tables record *incoming lots*: a ``Party`` delivered a quantity
of raw material (``InwardRawMaterial``, kilograms) or of a packing material
(``InwardOtherMaterial``, in its material type's unit) for a product's recipe.
An entry is booked the day it arrives (``created_at``); an other-material entry
is stamped with ``effective_date`` = that same day, while a raw lot stamps one
on the day the user flips it to ``in_use``. Dates never backfill into
middleware the way the snapshot dates do -- a lot counts toward stock only once
its effective date has come, so nothing surprises the books mid-day.

Read-time derivation (no stored counters, no cron): the raw-material stock of a
product is the sum of its ``quantity_kg`` over lots with ``status=in_use`` and
``effective_date <= today``; the on-hand of a material type is the sum of its
``InwardOtherMaterial.quantity`` over entries with ``effective_date <= today``.
A freshly recorded other-material lot is therefore in stock the day it arrives;
a raw lot counts only while its status is ``in_use`` -- flipping stamps today,
reverting clears the date and drops it back out of stock.

Raw material is also **spent** by bag and loose-packet counts recorded in
``InventoryOperations`` -- a lot's kilograms are packed into bags or sample
packets there. ``assert_raw_lot_removable`` guards the two ways a lot can
leave the ``in_use`` pool (reverting to ``lab_testing``, soft-deleting) so
neither can strand bags or packets that no longer have raw material behind
them.

Everything here is derived or shape-only: nothing in this module writes rows.
"""

from __future__ import annotations

from datetime import date
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
)

if TYPE_CHECKING:
    from .models import OtherMaterialRecipe, Party


# Two-way status transitions for an ``InwardRawMaterial`` lot. Editing this dict
# is the **only** change needed to change the flips: every guard below re-reads
# it on each call. Flipping to ``in_use`` stamps ``effective_date`` with today;
# reverting to ``lab_testing`` clears it (see ``UpdateInwardRawMaterialView``).
ALLOWED_RAW_STATUS_TRANSITIONS = {
    InwardRawMaterialStatus.LAB_TESTING: (InwardRawMaterialStatus.IN_USE,),
    InwardRawMaterialStatus.IN_USE: (InwardRawMaterialStatus.LAB_TESTING,),
}


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


def assert_raw_lot_removable(entry: InwardRawMaterial) -> None:
    """Raise unless ``entry`` may leave the in-use raw pool (revert or delete).

    Only a lot that is currently ``in_use`` *and* whose ``effective_date`` has
    come is counted in ``InventoryOperations.raw_available_kg`` at all --
    removing anything else (still ``lab_testing``, or dated in the future) is
    always safe. Removing a counted lot must not strand bags or sample packets
    that were packed from its kilograms with no raw material behind them.

    Raises ``ValueError`` with a message an API renders as a 400, the same
    convention as ``assert_raw_status_transition``.
    """
    is_counted = (
        entry.status == InwardRawMaterialStatus.IN_USE
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
        "quantity_kg": str(entry.quantity_kg),
        "status": entry.status,
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
    return {
        "public_id": entry.public_id,
        "recipe": {
            "public_id": recipe.public_id,
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


def raw_incoming_stock(
    as_of: date | None = None, *, product_public_ids: list[str] | None = None
) -> list[dict]:
    """Per-product incoming raw-material position as of ``as_of`` (default today).

    Only lots with ``status=in_use`` and ``effective_date <= as_of`` count
    toward ``incoming_kg``. ``packed_kg`` is what has since been packed into
    bags or sample packets (``InventoryOperations.raw_bagged_kg`` +
    ``raw_loose_kg``, read as of now -- a count has no "as of" of its own) and
    ``available_kg`` is what is left to pack. The list is ready for display:
    each entry carries the product's public id / name and Decimal kilogram
    figures (serializers turn them into strings). ``product_public_ids``
    narrows the report to those products.
    """
    as_of = as_of or today()
    query = InwardRawMaterial.objects.filter(
        effective_date__isnull=False,
        effective_date__lte=as_of,
        status=InwardRawMaterialStatus.IN_USE,
    )
    if product_public_ids:
        query = query.filter(product__public_id__in=product_public_ids)
    rows = list(
        query.values("product_id", "product__public_id", "product__name")
        .annotate(incoming_kg=Sum("quantity_kg"))
        .filter(incoming_kg__gt=0)
        .order_by("product__name")
    )
    products = Product.objects.in_bulk(row["product_id"] for row in rows)
    lines = []
    for row in rows:
        product = products[row["product_id"]]
        packed_kg = InventoryOperations.raw_bagged_kg(
            product
        ) + InventoryOperations.raw_loose_kg(product)
        lines.append(
            {
                "product_id": row["product_id"],
                "public_id": row["product__public_id"],
                "name": row["product__name"],
                "incoming_kg": row["incoming_kg"],
                "packed_kg": packed_kg,
                "available_kg": row["incoming_kg"] - packed_kg,
            }
        )
    return lines


def other_material_on_hand(
    as_of: date | None = None, *, material_type_ids: list[int] | None = None
) -> list[dict]:
    """Per-material-type on-hand position as of ``as_of`` (default today).

    Only entries with ``effective_date <= as_of`` count; the unit is the
    material type's own ``unit_type`` (count / kg / litre), so each line tells
    the reader how to read its ``on_hand`` number.
    ``material_type_ids`` narrows the report to those material types.
    """
    as_of = as_of or today()
    query = InwardOtherMaterial.objects.filter(
        effective_date__isnull=False,
        effective_date__lte=as_of,
    )
    if material_type_ids:
        query = query.filter(recipe__material_type_id__in=material_type_ids)
    rows = (
        query.values(
            "recipe__material_type_id",
            "recipe__material_type__name",
            "recipe__material_type__unit_type",
        )
        .annotate(on_hand=Sum("quantity"))
        .filter(on_hand__gt=0)
        .order_by("recipe__material_type__name")
    )
    return [
        {
            "material_type_id": row["recipe__material_type_id"],
            "name": row["recipe__material_type__name"],
            "unit_type": row["recipe__material_type__unit_type"],
            "on_hand": row["on_hand"],
        }
        for row in rows
    ]
