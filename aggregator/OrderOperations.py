"""Order lifecycle helpers for the ``aggregator`` sales domain.

Orders are exposed to the frontend by their ``public_id`` (``ORD-…``); payloads
never include the internal primary key.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.db import transaction

from common.models import indian_now

from .models import (
    DispatchDetails,
    Order,
    OrderItem,
    PrivateDispatchDetails,
    Status,
)
from .ProductOperations import packaging_payload


def _status(code: str) -> Status:
    return Status.objects.get(code=code)


@transaction.atomic
def create_order(
    *,
    client: Any,
    delivery_address: Any,
    actor: Any,
    items: Iterable[dict],
    status_code: str = "BOOKED",
    special_comments: str = "",
    expected_delivery_date=None,
) -> Order:
    """Create an order and its items atomically.

    Each entry in ``items`` is ``{"product_packaging", "negotiated_selling_price",
    "quantity"}``.
    """
    order = Order(
        client=client,
        delivery_address=delivery_address,
        status=_status(status_code),
        created_by=actor,
        special_comments=special_comments,
    )
    if expected_delivery_date is not None:
        order.expected_delivery_date = expected_delivery_date
    order.full_clean()
    order.save()

    for item in items:
        add_order_item(
            order,
            product_packaging=item["product_packaging"],
            negotiated_selling_price=item["negotiated_selling_price"],
            quantity=item["quantity"],
            actor=actor,
        )
    return order


def add_order_item(
    order: Order,
    *,
    product_packaging: Any,
    negotiated_selling_price,
    quantity: int,
    actor: Any,
) -> OrderItem:
    item = OrderItem(
        order=order,
        product_packaging=product_packaging,
        negotiated_selling_price=negotiated_selling_price,
        quantity=quantity,
        created_by=actor,
    )
    item.full_clean()
    item.save()
    return item


@transaction.atomic
def attach_dispatch_details(
    order: Order,
    *,
    dispatched_by: Any,
    dispatch_date,
    from_city: Any,
    to_city: Any,
    lr_number: str,
) -> DispatchDetails:
    """Record a third-party dispatch and link it to the order (clears private)."""
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
    order: Order,
    *,
    dispatched_by: Any,
    dispatch_date,
    from_city: Any,
    to_city: Any,
    vehicle_number: str,
    driver_number: str,
) -> PrivateDispatchDetails:
    """Record an own-vehicle dispatch and link it to the order (clears third-party)."""
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


def update_order_status(order: Order, status_code: str) -> Order:
    order.status = _status(status_code)
    order.full_clean()
    order.save(update_fields=["status", "updated_at"])
    return order


def mark_delivered(order: Order, actual_delivery_date=None) -> Order:
    order.status = _status("DELIVERED")
    order.actual_delivery_date = actual_delivery_date or indian_now().date()
    order.full_clean()
    order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    return order


def order_payload(order: Order) -> dict:
    """Frontend-facing dict for an order, keyed by public ids only."""
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
        "total_amount": str(order.total_amount),
        "total_bags": order.total_bags,
        "items": [
            {
                "packaging": packaging_payload(item.product_packaging),
                "negotiated_selling_price": str(item.negotiated_selling_price),
                "quantity": item.quantity,
                "line_total": str(item.line_total),
            }
            for item in order.items.select_related(
                "product_packaging__product"
            ).all()
        ],
    }
