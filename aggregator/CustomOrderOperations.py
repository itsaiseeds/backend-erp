"""Custom-order lifecycle helpers for the ``aggregator`` sales domain.

A custom order is the loose-packet counterpart of a normal :class:`Order`: its
lines are counted in loose packets and drawn from a packaging's loose pool, and it
may be booked only by a sales admin. It is a standalone record with no foreign
key to ``Order``.

Custom orders are exposed to the frontend by their ``public_id`` (``CORD-…``);
payloads never include the internal primary key.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from common.models import indian_now

from .models import (
    CustomOrder,
    CustomOrderItem,
    DispatchDetails,
    PrivateDispatchDetails,
    Status,
    StatusIds,
)


@transaction.atomic
def create_custom_order(
    *,
    client: Any,
    delivery_address: Any,
    actor: Any,
    items: Iterable[dict],
    special_comments: str = "",
    expected_delivery_date=None,
) -> CustomOrder:
    """Create a custom order and its loose-packet lines atomically.

    A custom order has **no separate verification step**: it is an admin
    instrument, so creating it *is* verifying it -- the order is born
    ``CONFIRMED`` with ``verified_by``/``verified_at`` set to the creating admin.

    ``actor`` must be a sales admin (enforced in ``CustomOrder.clean``). Each
    entry in ``items`` is ``{"product", "packets"}`` plus an optional
    ``"negotiated_selling_price"`` (per packet); when omitted the line uses the
    product's ``selling_price`` (the per-packet rate).

    **Stock gate:** there must be enough loose-packet stock. For every product
    line, the packets requested must not exceed what is currently available
    (`available_loose_packets`); otherwise the order is not created. Because the
    order confirms immediately, availability is checked *before* it reserves.
    """
    from . import InventoryOperations

    items = list(items)

    shortages = []
    for item in items:
        product = item["product"]
        needed = item["packets"]
        available = InventoryOperations.available_loose_packets(product)
        if needed > available:
            shortages.append(f"{product.name}: need {needed}, have {available}")
    if shortages:
        raise ValidationError(
            {
                "packets": (
                    "Not enough loose-packet stock to create this custom order -- "
                    f"{'; '.join(shortages)}."
                )
            }
        )

    order = CustomOrder(
        client=client,
        delivery_address=delivery_address,
        status=Status.by_id(StatusIds.CONFIRMED),
        created_by=actor,
        verified_by=actor,
        verified_at=indian_now(),
        special_comments=special_comments,
    )
    if expected_delivery_date is not None:
        order.expected_delivery_date = expected_delivery_date
    order.full_clean()
    order.save()

    for item in items:
        add_custom_order_item(
            order,
            product=item["product"],
            negotiated_selling_price=item.get("negotiated_selling_price"),
            packets=item["packets"],
            actor=actor,
        )
    return order


def add_custom_order_item(
    order: CustomOrder,
    *,
    product: Any,
    packets: int,
    actor: Any,
    negotiated_selling_price=None,
) -> CustomOrderItem:
    """Add a loose-packet line to ``order``.

    ``negotiated_selling_price`` overrides the per-packet price for this line only;
    omit it to charge ``product.selling_price``.
    """
    if negotiated_selling_price is None:
        negotiated_selling_price = product.selling_price
    item = CustomOrderItem(
        custom_order=order,
        product=product,
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
    dispatched_by: Any,
    dispatch_date,
    from_city: Any,
    to_city: Any,
    lr_number: str,
) -> DispatchDetails:
    """Record a third-party dispatch and link it to the custom order."""
    dispatch = DispatchDetails(
        client=order.client,
        dispatched_by=dispatched_by,
        dispatch_date=dispatch_date,
        from_city=from_city,
        to_city=to_city,
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
    dispatched_by: Any,
    dispatch_date,
    from_city: Any,
    to_city: Any,
    vehicle_number: str,
    driver_number: str,
) -> PrivateDispatchDetails:
    """Record an own-vehicle dispatch and link it to the custom order."""
    dispatch = PrivateDispatchDetails(
        client=order.client,
        dispatched_by=dispatched_by,
        dispatch_date=dispatch_date,
        from_city=from_city,
        to_city=to_city,
        vehicle_number=vehicle_number,
        driver_number=driver_number,
    )
    dispatch.full_clean()
    dispatch.save()

    order.private_dispatch_details = dispatch
    order.dispatch_details = None
    order.full_clean()
    order.save(update_fields=["dispatch_details", "private_dispatch_details", "updated_at"])
    return dispatch


def mark_delivered(order: CustomOrder, actual_delivery_date=None) -> CustomOrder:
    order.status = Status.by_id(StatusIds.DELIVERED)
    order.actual_delivery_date = actual_delivery_date or indian_now().date()
    order.full_clean()
    order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    return order


def revert_dispatch(order: CustomOrder) -> CustomOrder:
    """Reverse a dispatch, returning the custom order to ``CONFIRMED``.

    Its loose packets move back from consumed to reserved on their own -- both
    figures are derived from the status.
    """
    order.status = Status.by_id(StatusIds.CONFIRMED)
    order.actual_delivery_date = None
    order.full_clean()
    order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    return order


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
        "verified_at": order.verified_at.isoformat() if order.verified_at else None,
        "total_amount": str(order.total_amount),
        "total_packets": order.total_packets,
        "items": [
            {
                "product": {
                    "public_id": item.product.public_id,
                    "name": item.product.name,
                },
                "negotiated_selling_price": str(item.negotiated_selling_price),
                "packets": item.packets,
                "line_total": str(item.line_total),
            }
            for item in order.items.select_related("product").all()
        ],
    }
