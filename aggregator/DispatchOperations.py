"""Dispatch challan helpers: the ``DispatchEntry`` record and its payloads.

Where :mod:`aggregator.OrderOperations` owns the order's lifecycle, this module
owns the paperwork that lifecycle produces: the challan written when an order is
dispatched, the LR number recorded against it afterwards, and the payload the
challan list renders.

Everything here raises ``django.core.exceptions.ValidationError`` on a bad
request; ``api.exceptions.custom_exception_handler`` turns that into a 400.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from .AddressOperations import address_payload
from .CompanyDetails import COMPANY_DETAILS, DEFAULT_HSN_CODE, current_financial_year
from .models import DispatchEntry, DispatchEntryItem, Order
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
) -> DispatchEntry:
    """Write (or rewrite) ``order``'s challan and its lot-numbered lines.

    One entry per order, updated in place: an order that is reverted and
    dispatched again keeps its ``DE-...``, because it is the same order's challan
    and nothing outside has a reason to learn a new id for it.

    Call this **after** the dispatch details are attached -- the entry links
    ``order.dispatch_details``, and ``DispatchEntry.clean`` checks it is the
    order's own.
    """
    validated_lot_numbers(order, lot_numbers)

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

    # ``all_objects``: the order FK is unique, so a soft-deleted entry still
    # occupies the row this order would insert into.
    entry = DispatchEntry.all_objects.filter(order=order).first()
    if entry is None:
        entry = DispatchEntry(order=order, **values)
    else:
        entry.restore()
        for field in _ENTRY_FIELDS:
            setattr(entry, field, values[field])
    entry.full_clean()
    entry.save()

    _sync_entry_items(entry, order, lot_numbers, actor)
    return entry


def _sync_entry_items(
    entry: DispatchEntry,
    order: Order,
    lot_numbers: dict[str, str],
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
        line.quantity = item.quantity
        line.lot_number = lot_numbers[packaging.public_id]
        line.full_clean()
        line.save()
        lines.append(line)

    for stale in existing.values():
        stale.mark_deleted(actor)

    return lines


def set_lr_number(order: Order, *, lr_number: str):
    """Record the transporter's consignment note against ``order``'s dispatch.

    An LR number exists only where a third party carried the goods. A private
    (own-vehicle) dispatch has no transporter and so no consignment note, and a
    request to record one against it is a mistake worth reporting rather than a
    field to leave blank -- hence the 400.

    The number lands on ``DispatchDetails``, where it belongs; the challan reads
    it through ``DispatchEntry.lr_number``, so there is nothing else to write.
    """
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
    """
    entry = order.dispatch_entry
    items = list(entry.items.all())
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
        "dispatch": dispatch_entry_payload(entry),
        "items": [
            {
                **packaging_payload(line.product_packaging),
                "lot_number": line.lot_number,
                "quantity": line.quantity,
                "negotiated_selling_price": str(line.negotiated_selling_price),
                "line_total": str(line.line_total),
            }
            for line in items
        ],
        "item_count": len(items),
        "total_amount": str(entry.total_amount),
        "total_packets": entry.total_packets,
    }
