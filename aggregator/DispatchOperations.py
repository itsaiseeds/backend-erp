"""Dispatch challan helpers: the ``DispatchEntry`` record and its payloads.

Where :mod:`aggregator.OrderOperations` owns the order's lifecycle, this module
owns the paperwork that lifecycle produces: the challan written when an order is
dispatched, the LR number recorded against it afterwards, and the payload the
challan list renders.

A custom order's challan lives in the same ``DispatchEntry`` table (its
``custom_order`` set instead of ``order``), with loose lines keyed by
``(product, packet_weight)`` instead of a packaging -- see
:func:`sync_custom_dispatch_entry` and :func:`custom_dispatch_challan_payload`.

Everything here raises ``django.core.exceptions.ValidationError`` on a bad
request; ``api.exceptions.custom_exception_handler`` turns that into a 400.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .AddressOperations import address_payload
from .CompanyDetails import COMPANY_DETAILS, DEFAULT_HSN_CODE, current_financial_year
from .models import CustomOrder, DispatchEntry, DispatchEntryItem, Order
from .ProductOperations import packaging_payload

# Fields re-stamped every time an order is dispatched. The receiver snapshot and
# the journey are both re-taken: a re-dispatch may well go to a different city on
# a different lorry, and the client's contact may have changed since.
_ENTRY_FIELDS = (
    "dispatch_details",
    "client",
    "client_address",
    "contact_name",
    "contact_number",
    "dispatched_at",
    "from_city",
    "to_city",
    "vehicle_number",
    "driver_name",
    "driver_number",
)


def validated_lot_numbers(order: Order, lot_numbers: dict[str, str]) -> dict[str, str]:
    """Check ``lot_numbers`` names every line of ``order`` and nothing else.

    Keyed by ``ProductPackaging.public_id``, because that is the only packaging
    identifier the order detail payload exposes -- the primary key is never sent
    out, so a caller could not key by it.

    Every line needs one: a challan with a blank lot against a bag cannot be
    traced back to a batch, which is the whole point of recording it. Missing
    and unknown packagings are reported together so a caller fixes the form once
    rather than one id per round trip.
    """
    on_order = {item.product_packaging.public_id for item in order.items.all()}
    missing = sorted(on_order - lot_numbers.keys())
    unknown = sorted(lot_numbers.keys() - on_order)

    errors = []
    if missing:
        errors.append(f"No lot number for: {', '.join(missing)}.")
    if unknown:
        errors.append(f"Not on this order: {', '.join(unknown)}.")
    if errors:
        raise ValidationError({"items": " ".join(errors)})

    return lot_numbers


def validated_quantities(
    order: Order, quantities: dict[str, int] | None
) -> dict[str, int]:
    """Check ``quantities`` names a subset of ``order``'s lines, each within bounds.

    Keyed the same way as ``lot_numbers``. A line missing from ``quantities``
    (or ``quantities`` being ``None`` entirely) dispatches in full -- most
    dispatches ship everything ordered, so nothing has to be repeated back for
    the common case. A named quantity must be more than zero and no more than
    that line's ordered quantity: a dispatch can fall short of an order, never
    exceed it.
    """
    quantities = quantities or {}
    on_order = {item.product_packaging.public_id: item.quantity for item in order.items.all()}
    unknown = sorted(quantities.keys() - on_order.keys())
    if unknown:
        raise ValidationError({"items": f"Not on this order: {', '.join(unknown)}."})

    errors = []
    for public_id, quantity in quantities.items():
        ordered = on_order[public_id]
        if quantity <= 0 or quantity > ordered:
            errors.append(
                f"{public_id}: dispatched quantity must be between 1 and {ordered}, "
                f"got {quantity}."
            )
    if errors:
        raise ValidationError({"items": " ".join(errors)})

    return quantities


@transaction.atomic
def sync_dispatch_entry(
    order: Order,
    *,
    actor,
    dispatched_at,
    from_city,
    to_city,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
    lot_numbers: dict[str, str],
    quantities: dict[str, int] | None = None,
) -> DispatchEntry:
    """Write (or rewrite) ``order``'s challan and its lot-numbered lines.

    One entry per order, updated in place: an order that is reverted and
    dispatched again keeps its ``DE-...``, because it is the same order's challan
    and nothing outside has a reason to learn a new id for it.

    ``quantities`` names, per line, how many actually shipped -- a line left out
    ships in full. See ``validated_quantities`` and ``DispatchEntryItem`` for
    what a partial figure means for stock.

    Call this **after** the dispatch details are attached -- the entry links
    ``order.dispatch_details``, and ``DispatchEntry.clean`` checks it is the
    order's own.
    """
    validated_lot_numbers(order, lot_numbers)
    quantities = validated_quantities(order, quantities)

    entry = _upsert_entry(
        {"order": order},
        order,
        dispatched_at=dispatched_at,
        from_city=from_city,
        to_city=to_city,
        driver_name=driver_name,
        driver_number=driver_number,
        vehicle_number=vehicle_number,
    )
    _sync_entry_items(entry, order, lot_numbers, actor)
    return entry


def _upsert_entry(
    lookup: dict[str, Order | CustomOrder],
    order: Order | CustomOrder,
    *,
    dispatched_at,
    from_city,
    to_city,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
) -> DispatchEntry:
    """Write (or rewrite in place) the challan header for ``order``.

    ``lookup`` names the order the entry hangs off -- ``{"order": ...}`` or
    ``{"custom_order": ...}``. Read through ``all_objects``: the FK is unique,
    so a soft-deleted entry still occupies the row this order would insert
    into.
    """
    contact = order.client.primary_contact
    values = {
        "dispatch_details": order.dispatch_details,
        "client": order.client,
        "client_address": order.delivery_address,
        "contact_name": contact.name if contact else "",
        "contact_number": contact.phone_number if contact else "",
        "dispatched_at": dispatched_at,
        "from_city": from_city,
        "to_city": to_city,
        "vehicle_number": vehicle_number,
        "driver_name": driver_name,
        "driver_number": driver_number,
    }

    entry = DispatchEntry.all_objects.filter(**lookup).first()
    if entry is None:
        entry = DispatchEntry(**lookup, **values)
    else:
        entry.restore()
        for field in _ENTRY_FIELDS:
            setattr(entry, field, values[field])
    entry.full_clean()
    entry.save()

    _sync_entry_items(entry, order, lot_numbers, quantities, actor)
    return entry


def _sync_entry_items(
    entry: DispatchEntry,
    order: Order,
    lot_numbers: dict[str, str],
    quantities: dict[str, int],
    actor,
) -> list[DispatchEntryItem]:
    """Mirror ``order``'s lines onto ``entry``, stamping each with its lot number.

    Looked up through ``all_objects`` for the same reason
    ``OrderOperations.sync_order_items`` does: the natural-key unique constraint
    is not soft-delete aware, so a packaging dropped from the order and later put
    back must have its original row restored rather than a second one inserted.
    """
    existing = {
        line.product_packaging_id: line
        for line in DispatchEntryItem.all_objects.filter(dispatch_entry=entry)
    }

    lines: list[DispatchEntryItem] = []
    for item in order.items.all():
        packaging = item.product_packaging
        line = existing.pop(packaging.pk, None)
        if line is None:
            line = DispatchEntryItem(
                dispatch_entry=entry,
                product_packaging=packaging,
                created_by=actor,
            )
        else:
            line.restore()
        line.negotiated_selling_price = item.negotiated_selling_price
        line.quantity = quantities.get(packaging.public_id, item.quantity)
        line.lot_number = lot_numbers[packaging.public_id]
        line.full_clean()
        line.save()
        lines.append(line)

    for stale in existing.values():
        stale.mark_deleted(actor)

    return lines


LooseLotKey = tuple[str, Decimal]


def validated_loose_lot_numbers(
    order: CustomOrder, lot_numbers: dict[LooseLotKey, str]
) -> dict[LooseLotKey, str]:
    """Check ``lot_numbers`` names every line of custom ``order`` and nothing else.

    The loose-line counterpart of :func:`validated_lot_numbers`, keyed by
    ``(product public id, packet_weight)`` -- the pair that identifies a line on
    the custom order detail payload.
    """
    on_order = {
        (item.product.public_id, item.packet_weight) for item in order.items.all()
    }
    missing = sorted(on_order - lot_numbers.keys())
    unknown = sorted(lot_numbers.keys() - on_order)

    def names(keys: list[LooseLotKey]) -> str:
        return ", ".join(f"{public_id} @ {weight}kg" for public_id, weight in keys)

    errors = []
    if missing:
        errors.append(f"No lot number for: {names(missing)}.")
    if unknown:
        errors.append(f"Not on this custom order: {names(unknown)}.")
    if errors:
        raise ValidationError({"items": " ".join(errors)})

    return lot_numbers


@transaction.atomic
def sync_custom_dispatch_entry(
    order: CustomOrder,
    *,
    actor,
    dispatched_at,
    from_city,
    to_city,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
    lot_numbers: dict[LooseLotKey, str],
) -> DispatchEntry:
    """Write (or rewrite) custom ``order``'s challan and its lot-numbered loose lines.

    The same contract as :func:`sync_dispatch_entry`: one entry per custom
    order, updated in place on a re-dispatch, written **after** the dispatch
    record is attached.
    """
    validated_loose_lot_numbers(order, lot_numbers)

    entry = _upsert_entry(
        {"custom_order": order},
        order,
        dispatched_at=dispatched_at,
        from_city=from_city,
        to_city=to_city,
        driver_name=driver_name,
        driver_number=driver_number,
        vehicle_number=vehicle_number,
    )

    existing = {
        (line.product_id, line.packet_weight): line
        for line in DispatchEntryItem.all_objects.filter(dispatch_entry=entry)
    }
    for item in order.items.select_related("product"):
        line = existing.pop((item.product_id, item.packet_weight), None)
        if line is None:
            line = DispatchEntryItem(
                dispatch_entry=entry,
                product=item.product,
                packet_weight=item.packet_weight,
                created_by=actor,
            )
        else:
            line.restore()
        line.negotiated_selling_price = item.negotiated_selling_price
        line.quantity = item.packets
        line.lot_number = lot_numbers[(item.product.public_id, item.packet_weight)]
        line.full_clean()
        line.save()

    for stale in existing.values():
        stale.mark_deleted(actor)

    return entry


def set_lr_number(order: Order, *, lr_number: str):
    """Record the transporter's consignment note against ``order``'s dispatch.

    An LR number exists only where a third party carried the goods. A private
    (own-vehicle) dispatch has no transporter and so no consignment note, and a
    request to record one against it is a mistake worth reporting rather than a
    field to leave blank -- hence the 400.

    The number lands on ``DispatchDetails``, where it belongs; the challan reads
    it through ``DispatchEntry.lr_number``, so there is nothing else to write.

    Only a DISPATCHED or DELIVERED order takes one. A reverted dispatch keeps its
    dispatch record, so that alone would let an LR land on goods still on the
    shelf; the status check comes after the record checks so an undispatched or
    private order keeps its more specific message.
    """
    from .OrderOperations import LR_RECORDABLE_STATUS_CODES, assert_order_status

    dispatch = order.dispatch_details
    if dispatch is None:
        if order.private_dispatch_details_id:
            raise ValidationError(
                {
                    "lr_number": (
                        "This order went on our own vehicle, so there is no "
                        "transporter to issue an LR number."
                    )
                }
            )
        raise ValidationError({"lr_number": "This order has not been dispatched yet."})

    assert_order_status(order, LR_RECORDABLE_STATUS_CODES, "record an LR number for")

    dispatch.lr_number = lr_number.strip()
    dispatch.full_clean()
    dispatch.save(update_fields=["lr_number", "updated_at"])
    return dispatch


def dispatch_entry_payload(entry: DispatchEntry) -> dict:
    """The journey block of a challan: who carried it, in what, when and where."""
    return {
        "public_id": entry.public_id,
        "lr_number": entry.lr_number,
        "dispatch_date": entry.dispatch_date.isoformat(),
        "is_private": entry.is_private,
        "vehicle_number": entry.vehicle_number,
        "driver_name": entry.driver_name,
        "driver_number": entry.driver_number,
        "from_city": entry.from_city.name,
        "to_city": entry.to_city.name,
    }


def dispatch_challan_payload(order: Order) -> dict:
    """One printable challan: consignor, consignee, journey and lot-numbered lines.

    The receiver block is read off the ``DispatchEntry`` snapshot rather than the
    live client, so a challan reprinted next year still says what went out with
    the goods.

    The transport agency is read off the order: it is chosen at booking, decides
    the dispatch mode, and cannot be edited once the order has been dispatched.
    Null on a private dispatch, where there is no carrier.
    """
    entry = order.dispatch_entry
    items = list(entry.items.all())
    agency = order.transport_agency
    return {
        **_challan_header(order, entry),
        "dispatch": {
            **dispatch_entry_payload(entry),
            "transport_agency": (
                {"id": agency.id, "name": agency.name} if agency else None
            ),
        },
        "items": [_bag_line_payload(line) for line in items],
        "item_count": len(items),
        "total_amount": str(entry.total_amount),
        "total_packets": entry.total_packets,
    }


def _challan_header(order: Order | CustomOrder, entry: DispatchEntry) -> dict:
    """The part of a challan that is the same for either kind of order."""
    return {
        "order_public_id": order.public_id,
        "our_details": dict(COMPANY_DETAILS),
        "receiver_details": {
            "company_name": entry.client.company_name,
            "gst_number": entry.client.gst_number,
            "address": address_payload(entry.client_address),
            "contact_person_name": entry.contact_name,
            "contact_person_number": entry.contact_number,
        },
        "hsn_code": DEFAULT_HSN_CODE,
        "financial_year": current_financial_year(entry.dispatch_date),
    }


def custom_dispatch_challan_payload(order: CustomOrder) -> dict:
    """One printable challan for a custom order.

    The same envelope as :func:`dispatch_challan_payload`, with ``order_type``
    set so a reader can tell the rows apart, and loose lines: a product, the
    weight of one packet, how many packets, the lot and the money. A custom
    order has no transport agency, so the dispatch block's is always null.
    """
    entry = order.dispatch_entry
    items = list(entry.items.all())
    return {
        **_challan_header(order, entry),
        "order_type": "CUSTOM_ORDER",
        "dispatch": {**dispatch_entry_payload(entry), "transport_agency": None},
        "items": [_loose_line_payload(line) for line in items],
        "item_count": len(items),
        "total_amount": str(entry.total_amount),
        "total_packets": entry.total_packets,
    }


def _bag_line_payload(line: DispatchEntryItem) -> dict:
    """One bag line of an order's challan."""
    packaging = line.product_packaging
    if packaging is None:
        raise ValueError(f"Dispatch entry item {line.pk} is not a bag line.")
    return {
        **packaging_payload(packaging),
        "lot_number": line.lot_number,
        "quantity": line.quantity,
        "negotiated_selling_price": str(line.negotiated_selling_price),
        "line_total": str(line.line_total),
    }


def _loose_line_payload(line: DispatchEntryItem) -> dict:
    """One loose-packet line of a custom order's challan."""
    product = line.product
    if product is None:
        raise ValueError(f"Dispatch entry item {line.pk} is not a loose line.")
    return {
        "product": {"public_id": product.public_id, "name": product.name},
        "packet_weight": str(line.packet_weight),
        "packets": line.quantity,
        "lot_number": line.lot_number,
        "negotiated_selling_price": str(line.negotiated_selling_price),
        "line_total": str(line.line_total),
    }


def challan_entry_payload(entry: DispatchEntry) -> dict:
    """The challan for ``entry``, whichever kind of order it belongs to."""
    if entry.order is not None:
        return dispatch_challan_payload(entry.order)
    if entry.custom_order is not None:
        return custom_dispatch_challan_payload(entry.custom_order)
    raise ValueError(f"Dispatch entry {entry.public_id} names no order.")
