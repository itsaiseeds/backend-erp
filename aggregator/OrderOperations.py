"""Order lifecycle helpers for the ``aggregator`` sales domain.

Orders are exposed to the frontend by their ``public_id`` (``ORD-…``); payloads
never include the internal primary key.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from common.models import indian_now

from .models import (
    Address,
    City,
    Client,
    DispatchDetails,
    Order,
    OrderItem,
    PrivateDispatchDetails,
    ProductPackaging,
    Status,
    StatusIds,
    TransportAgency,
)
from .ProductOperations import packaging_payload

if TYPE_CHECKING:
    from authentication.models import User


@transaction.atomic
def create_order(
    *,
    client: Client,
    delivery_address: Address,
    actor: User,
    items: Iterable[dict],
    status: StatusIds = StatusIds.BOOKED,
    special_comments: str = "",
    expected_delivery_date=None,
    transport_agency: TransportAgency | None = None,
) -> Order:
    """Create an order and its items atomically.

    Each entry in ``items`` is ``{"product_packaging", "quantity"}`` plus an
    optional ``"negotiated_selling_price"``. When omitted, the item line uses
    ``product_packaging.selling_price`` (the whole-packaging price captured on
    the packaging at creation).

    ``transport_agency`` must be one of the client's own agencies (``Order.clean``
    enforces it). Leave it ``None`` for a private, own-vehicle dispatch -- the
    default assumption.
    """
    order = Order(
        client=client,
        delivery_address=delivery_address,
        status=Status.by_id(status),
        created_by=actor,
        special_comments=special_comments,
        transport_agency=transport_agency,
    )
    if expected_delivery_date is not None:
        order.expected_delivery_date = expected_delivery_date
    order.full_clean()
    order.save()

    for item in items:
        add_order_item(
            order,
            product_packaging=item["product_packaging"],
            negotiated_selling_price=item.get("negotiated_selling_price"),
            quantity=item["quantity"],
            actor=actor,
        )
    return order


def add_order_item(
    order: Order,
    *,
    product_packaging: ProductPackaging,
    quantity: int,
    actor: User,
    negotiated_selling_price=None,
) -> OrderItem:
    """Add a line to ``order``.

    ``negotiated_selling_price`` overrides the packaging's list price for this
    line only; omit it to charge ``product_packaging.selling_price``.
    """
    if negotiated_selling_price is None:
        negotiated_selling_price = product_packaging.selling_price
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
    dispatched_by: User,
    dispatch_date,
    from_city: City,
    to_city: City,
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
    dispatched_by: User,
    dispatch_date,
    from_city: City,
    to_city: City,
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


def update_order_status(order: Order, status: StatusIds) -> Order:
    order.status = Status.by_id(status)
    order.full_clean()
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def verify_order(order: Order, admin: User) -> Order:
    """Mark ``order`` verified, recording the acting sales admin and time.

    Three gates apply:

    * ``admin`` must hold an ``Admin`` profile (or be a superuser). Note that
      ``can_update_stock_count`` is deliberately **not** checked here -- that
      flag gates writing an ``InventorySnapshot``, nothing else.
    * today's stock count must be complete, i.e. every active packaging has been
      counted. No count, no verification.
    * there must be enough available stock: for every packaging on the order,
      the bags it needs must not exceed what is still available (on hand minus
      already reserved/consumed). Not enough stock, no verification.
    """
    from . import InventoryOperations

    if not (admin is not None and (admin.is_admin_user or admin.is_superuser)):
        raise PermissionDenied("Orders can only be verified by a sales admin.")

    if not InventoryOperations.is_stock_count_complete():
        missing = list(
            InventoryOperations.missing_packagings().values_list("public_id", flat=True)
        )
        raise ValidationError(
            {
                "status": (
                    "Today's stock count is incomplete -- orders cannot be verified. "
                    f"Missing packagings: {', '.join(missing)}."
                )
            }
        )

    shortages = []
    for packaging, needed in InventoryOperations.order_bag_requirements(order).items():
        available = InventoryOperations.available_bags(packaging)
        if needed > available:
            shortages.append(f"{packaging.public_id}: need {needed}, have {available}")
    if shortages:
        raise ValidationError(
            {
                "status": (
                    "Not enough stock to verify this order -- "
                    f"{'; '.join(shortages)}."
                )
            }
        )

    order.status = Status.by_id(StatusIds.CONFIRMED)
    order.verified_by = admin
    order.verified_at = indian_now()
    order.full_clean()
    order.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
    return order


@transaction.atomic
def unverify_order(order: Order, *, status: StatusIds = StatusIds.UNDER_REVIEW) -> Order:
    """Reverse a verification, clearing who verified it and when.

    The bags this order was holding are released automatically: reservations
    are derived from ``Order.status``, never stored.
    """
    order.status = Status.by_id(status)
    order.verified_by = None
    order.verified_at = None
    order.full_clean()
    order.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
    return order


def revert_dispatch(order: Order) -> Order:
    """Reverse a dispatch, returning the order to ``CONFIRMED``.

    Its bags move back from consumed to reserved on their own, for the same
    reason: both figures are derived from the status.
    """
    order.status = Status.by_id(StatusIds.CONFIRMED)
    order.actual_delivery_date = None
    order.full_clean()
    order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    return order


def mark_delivered(order: Order, actual_delivery_date=None) -> Order:
    order.status = Status.by_id(StatusIds.DELIVERED)
    order.actual_delivery_date = actual_delivery_date or indian_now().date()
    order.full_clean()
    order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    return order


def order_payload(order: Order) -> dict:
    """Frontend-facing dict for an order, keyed by public ids only.

    ``dispatch_mode`` is derived, not stored: an order with no transport agency
    is dispatched privately (own vehicle), which is the default.
    """
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
        "transport_agency": (
            {"id": order.transport_agency_id, "name": order.transport_agency.name}
            if order.transport_agency_id
            else None
        ),
        "dispatch_mode": "AGENCY" if order.transport_agency_id else "PRIVATE",
        "verified_at": order.verified_at.isoformat() if order.verified_at else None,
        "total_amount": str(order.total_amount),
        "total_packets": order.total_packets,
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
