"""Order lifecycle helpers for the ``aggregator`` sales domain.

Orders are exposed to the frontend by their ``public_id`` (``ORD-…``); payloads
never include the internal primary key.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from common.models import indian_now

from .ClientChildOrgOperations import child_org_payload, child_org_summary_payload
from .ClientOperations import client_payload, client_summary_payload, order_city_payload
from .models import (
    Address,
    City,
    Client,
    ClientChildOrg,
    DispatchDetails,
    Order,
    OrderItem,
    PrivateDispatchDetails,
    ProductPackaging,
    ReturnOrder,
    Status,
    StatusIds,
    StockEventDetail,
    StockEventType,
    TransportAgency,
)
from .models.ReturnOrder import LIVE_RETURN_STATUS_IDS
from .NotificationOperations import NotificationEvent, notify_order_event
from .ProductOperations import assert_products_usable, packaging_payload
from .ReturnOrderOperations import live_return_orders, order_return_payload, return_order_payload
from .StockLedgerOperations import dispatch_detail, order_product_ids, recording

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
    booked_for: ClientChildOrg | None = None,
) -> Order:
    """Create an order and its items atomically.

    Each entry in ``items`` is ``{"product_packaging", "quantity"}`` plus an
    optional ``"negotiated_selling_price"``. When omitted, the item line uses
    ``product_packaging.selling_price`` (the whole-packaging price captured on
    the packaging at creation).

    ``transport_agency`` must be one of the client's own agencies (``Order.clean``
    enforces it). Leave it ``None`` for a private, own-vehicle dispatch -- the
    default assumption.

    ``booked_for`` is the client's child org the order is booked on behalf of
    (``Order.clean`` checks it belongs to the client).

    Refused (400) when any line's product is not usable.
    """
    items = list(items)
    assert_products_usable(
        [item["product_packaging"].product_id for item in items],
        field="items",
        action="be ordered",
        subject="this order",
    )
    order = Order(
        client=client,
        delivery_address=delivery_address,
        status=Status.by_id(status),
        created_by=actor,
        special_comments=special_comments,
        transport_agency=transport_agency,
        booked_for=booked_for,
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
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
    lr_number: str = "",
) -> DispatchDetails:
    """Record a third-party dispatch and link it to the order (clears private).

    The driver and the vehicle are required even though a transporter is
    carrying the goods: they are what a delivery query is chased with.

    ``lr_number`` is the exception -- the carrier usually issues the consignment
    note after collection, so a dispatch is recorded while it is still pending.
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
    order: Order,
    *,
    dispatched_by: User,
    dispatch_date,
    from_city: City,
    to_city: City,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
) -> PrivateDispatchDetails:
    """Record an own-vehicle dispatch and link it to the order (clears third-party)."""
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


def update_order_status(order: Order, status: StatusIds) -> Order:
    order.status = Status.by_id(status)
    order.full_clean()
    order.save(update_fields=["status", "updated_at"])
    return order


# -- Lifecycle transitions ----------------------------------------------------
#
# Each verb below declares the statuses it may be applied from. The sets are
# derived from ``StatusIds`` rather than spelled out, so renaming a status is a
# one-line change in the enum. ``assert_order_status`` is the single gate; the verbs
# differ only in which set they hand it.
#
# UNDER_REVIEW is verifiable *because* ``unverify_order`` lands there -- without
# it, unverifying would be a one-way trap with no route back to CONFIRMED.
# REJECTED appears in no set: rejection is terminal.

VERIFIABLE_STATUS_CODES = frozenset(
    {StatusIds.BOOKED.name, StatusIds.UNDER_REVIEW.name, StatusIds.ON_HOLD.name}
)
UNVERIFIABLE_STATUS_CODES = frozenset({StatusIds.CONFIRMED.name})
DISPATCHABLE_STATUS_CODES = frozenset({StatusIds.CONFIRMED.name})
REVERTIBLE_DISPATCH_STATUS_CODES = frozenset({StatusIds.DISPATCHED.name})
DELIVERABLE_STATUS_CODES = frozenset({StatusIds.DISPATCHED.name})
HOLDABLE_STATUS_CODES = frozenset(
    {StatusIds.BOOKED.name, StatusIds.UNDER_REVIEW.name, StatusIds.CONFIRMED.name}
)
REJECTABLE_STATUS_CODES = HOLDABLE_STATUS_CODES | {StatusIds.ON_HOLD.name}
# An LR is the transporter's note for goods that actually left. A reverted
# dispatch (back to CONFIRMED) keeps its dispatch record, so the record alone
# does not prove the goods are on the road -- the status does.
LR_RECORDABLE_STATUS_CODES = frozenset(
    {StatusIds.DISPATCHED.name, StatusIds.DELIVERED.name}
)

# Only a freshly booked order or a confirmed one may be edited. Every other
# status is refused: DISPATCHED/DELIVERED because the goods have physically
# left, REJECTED because rejection is terminal, and UNDER_REVIEW/ON_HOLD because
# they are parked awaiting a decision -- verify the order first, then edit it.
# Editing a CONFIRMED order re-checks stock (see ``sync_order_items``).
EDITABLE_STATUS_CODES = frozenset({StatusIds.BOOKED.name, StatusIds.CONFIRMED.name})


def assert_order_status(order: Order, allowed: frozenset[str], action: str) -> None:
    """Guard a lifecycle transition on the order's current status.

    Raises ``ValidationError``, which the API's exception handler turns into a
    400 -- this is a rejected request, not a server fault.
    """
    code = order.status.code if order.status_id else None
    if code not in allowed:
        raise ValidationError(
            {
                "status": (
                    f"Cannot {action} an order that is {code}. "
                    f"Allowed: {', '.join(sorted(allowed))}."
                )
            }
        )


def assert_dispatched_today(order) -> None:
    """Raise unless ``order``'s dispatch was recorded today (IST).

    A revert is a correction of something just recorded, not a time machine.
    Rewinding an older dispatch moves its bags from consumed back to reserved
    against *today's* stock position, and the re-dispatch that follows re-stamps
    ``dispatched_at`` with today -- so a consignment that physically left on the
    1st would silently become one that left today, challan number and all.

    Shared by ``revert_dispatch`` here and its ``CustomOrderOperations``
    counterpart, and called **after** each one's status check so the existing
    "an order that is CONFIRMED" refusal still comes first. It takes no
    ``action`` word, unlike ``assert_order_status``: revert is the only verb
    this rule applies to, and threading one through only made the message say
    "dispatch" twice.

    The day is read off the challan, which is the timestamp a re-dispatch
    re-stamps. A DISPATCHED order with no challan is reachable (dispatch rows
    attached and the status moved directly, as some tests do), so the dispatch
    record itself is the fallback -- ``Order.clean`` guarantees one of the two
    is there once the order is DISPATCHED.

    Raises ``ValidationError``, which the API's exception handler turns into a
    400, the same convention as ``assert_order_status``.
    """
    entry = getattr(order, "dispatch_entry", None)
    dispatch = entry if entry is not None else order.active_dispatch
    if dispatch is None:
        return
    day = dispatch.dispatch_date
    # ``indian_now().date()`` rather than ``InventoryOperations.today()``: the
    # same value, without the local import that module needs here (and the same
    # call ``mark_delivered`` below already makes).
    if day != indian_now().date():
        raise ValidationError(
            {
                "status": (
                    f"This dispatch was recorded on {day:%Y-%m-%d}: only a "
                    "dispatch recorded today can be reverted."
                )
            }
        )


# The refusal an own-vehicle dispatch gets per blank field. Declared here, with
# the rule, and reused by ``DispatchCustomOrderView`` so the serializer that
# re-requires these fields answers in exactly the same words.
OWN_VEHICLE_FIELD_REQUIRED = "{field} is required on an own-vehicle dispatch."


def assert_driver_details(
    driver_name: str, driver_number: str, vehicle_number: str
) -> None:
    """Raise unless an own-vehicle dispatch names its driver and vehicle.

    All three are optional on an **agency** dispatch: the agency assigns the
    vehicle and often only tells us which one after collection, so a blank there
    is a detail still to come. Our own vehicle always has a known driver, so a
    blank is a mistake, and recording one would put an unchaseable consignment
    on the road.

    This lives beside ``assert_order_status`` rather than in the serializer
    because which kind of dispatch it is comes from the *order*
    (``transport_agency``), not from the request -- the same reason
    ``dispatch_order`` picks the ``attach`` function off the order. The custom
    order path calls it unconditionally: a custom order is always own-vehicle.

    Raises ``ValidationError``, which the API's exception handler turns into a
    400, naming every field that was left blank.
    """
    blanks = {
        field: OWN_VEHICLE_FIELD_REQUIRED.format(field=field)
        for field, value in (
            ("driver_name", driver_name),
            ("driver_number", driver_number),
            ("vehicle_number", vehicle_number),
        )
        if not value
    }
    if blanks:
        raise ValidationError(blanks)


def assert_stock_covers(
    needed: Mapping[ProductPackaging, int],
    action: str,
    *,
    held: Mapping[ProductPackaging, int] | None = None,
) -> None:
    """Raise unless today's stock can supply ``needed`` bags per packaging.

    ``held`` is what the order already reserves (a CONFIRMED order's current
    lines). ``available_bags`` has already netted it off, so it is added back
    before comparing -- otherwise the order would be counted against itself.
    A packaging whose need does not exceed what is held asks for nothing new
    and is not checked, so shrinking an order is never refused.

    Two gates, the same ones verification applies: today's stock count must be
    complete, and every packaging must have the bags. Raises
    ``ValidationError``, which the API turns into a 400.

    **The packagings being grown are locked before availability is read**
    (:func:`InventoryOperations.lock_bag_pools`) and stay locked until the
    caller's transaction commits the reservation. Without it two orders
    verified at the same moment would both read the same available figure and
    together reserve more bags than exist. Callers must therefore be inside
    ``transaction.atomic`` and write their reservation in that same block.
    """
    from . import InventoryOperations

    held = held or {}
    increases = {
        packaging: bags
        for packaging, bags in needed.items()
        if bags > held.get(packaging, 0)
    }
    if not increases:
        return

    InventoryOperations.lock_bag_pools(increases)

    if not InventoryOperations.is_stock_count_complete():
        missing = [
            str(packaging)
            for packaging in InventoryOperations.missing_packagings().select_related("product")
        ]
        raise ValidationError(
            {
                "status": (
                    f"Today's stock count is incomplete -- cannot {action} this order. "
                    f"Missing packagings: {', '.join(missing)}."
                )
            }
        )

    shortages = []
    for packaging, bags in increases.items():
        available = InventoryOperations.available_bags(packaging) + held.get(packaging, 0)
        if bags > available:
            shortages.append(f"{packaging}: need {bags}, have {available}")
    if shortages:
        raise ValidationError(
            {
                "status": (
                    f"Not enough stock to {action} this order -- "
                    f"{'; '.join(shortages)}."
                )
            }
        )


def hold_order(order: Order, *, actor: User) -> Order:
    """Put ``order`` on hold.

    A held order reserves nothing: reservations are derived from the status, so
    holding a CONFIRMED order releases its bags with no bookkeeping.
    """
    assert_order_status(order, HOLDABLE_STATUS_CODES, "hold")
    with recording(
        StockEventType.ORDER_RELEASED,
        StockEventDetail.HELD,
        order_product_ids(order),
        source=order,
    ):
        update_order_status(order, StatusIds.ON_HOLD)
    notify_order_event(order, NotificationEvent.ORDER_ON_HOLD, actor=actor)
    return order


def reject_order(order: Order, *, actor: User) -> Order:
    """Reject ``order``. Terminal: no verb moves an order out of REJECTED."""
    assert_order_status(order, REJECTABLE_STATUS_CODES, "reject")
    with recording(
        StockEventType.ORDER_RELEASED,
        StockEventDetail.REJECTED,
        order_product_ids(order),
        source=order,
    ):
        update_order_status(order, StatusIds.REJECTED)
    notify_order_event(order, NotificationEvent.ORDER_REJECTED, actor=actor)
    return order


@transaction.atomic
def dispatch_order(
    order: Order,
    *,
    actor: User,
    from_city: City,
    driver_name: str,
    driver_number: str,
    vehicle_number: str,
    lot_numbers: dict[str, str],
    quantities: dict[str, int] | None = None,
) -> Order:
    """Record a dispatch against a verified order and move it to DISPATCHED.

    Only a CONFIRMED order can be dispatched -- an unverified order has not been
    checked against stock, so shipping it would consume bags nobody confirmed
    were there.

    **Which kind of dispatch this is comes from the order, not from the
    arguments**: an order carrying a ``transport_agency`` goes by that carrier
    and the details land on ``DispatchDetails``; one without goes on our own
    vehicle and they land on ``PrivateDispatchDetails``. That is the same rule
    ``dispatch_mode`` reports on every order payload, so what was planned at
    booking time is what gets recorded. Both kinds take the same details -- who
    drove, on what number, in which vehicle -- so the caller supplies one shape
    either way.

    **How strict those details are also comes from the order.** On an agency
    dispatch all three may be blank: the agency assigns the vehicle, and often
    only says which after collection. On an own-vehicle dispatch all three are
    required (``assert_driver_details``), because our own vehicle always has a
    known driver.

    Two things are **derived, not passed**: the dispatch date is today (the
    dispatch is being recorded as it happens), and the destination is the city
    of the order's own delivery address, which is where the goods are going by
    definition. ``from_city`` stays an argument until there is a warehouse to
    default it from.

    The ``lr_number`` is not set here. It is the one field a transporter issues
    after collection, so a dispatch is always recorded without it -- it is
    recorded later by ``DispatchOperations.set_lr_number``. Re-dispatching
    therefore drops the previous LR with the previous ``DispatchDetails`` row:
    that note described the previous journey.

    ``lot_numbers`` maps each line's ``ProductPackaging.public_id`` to the batch
    those bags came from, and must name every line exactly once. It is what the
    challan is written from: the dispatch itself is one journey, but the goods
    on it are traced batch by batch.

    ``quantities`` maps a line to how many bags actually shipped, when that
    falls short of what was ordered; a line left out ships in full. A shortfall
    does not vanish -- it stays reserved against this same order (see
    ``InventoryOperations.reserved_bags``) until someone corrects it by hand,
    since dispatch is a one-shot action and there is no later shipment to
    finish the line.

    The details are attached *before* the status moves: ``Order.clean`` rejects
    a DISPATCHED order that carries no dispatch record, so the other order would
    fail validation. No stock is written -- CONFIRMED to DISPATCHED moves the
    bags from reserved to consumed on its own.
    """
    from .DispatchOperations import (
        sync_dispatch_entry,
        validated_lot_numbers,
        validated_quantities,
    )

    assert_order_status(order, DISPATCHABLE_STATUS_CODES, "dispatch")

    # Validated before anything is written, so a bad lot number costs nothing.
    validated_lot_numbers(order, lot_numbers)
    validated_quantities(order, quantities)
    # The order decides both which table the dispatch lands on and whether the
    # driver details were optional, so the two reads of ``transport_agency_id``
    # below can never disagree.
    if not order.transport_agency_id:
        assert_driver_details(driver_name, driver_number, vehicle_number)

    dispatched_at = indian_now()
    to_city = order.delivery_address.city

    attach = (
        attach_dispatch_details
        if order.transport_agency_id
        else attach_private_dispatch_details
    )
    with recording(
        StockEventType.ORDER_DISPATCHED,
        StockEventDetail.FULL,
        order_product_ids(order),
        source=order,
        actor=actor,
    ) as rec:
        assert_products_usable(
            order_product_ids(order),
            field="status",
            action="be dispatched",
            subject="this order",
        )
        attach(
            order,
            dispatched_by=actor,
            dispatch_date=dispatched_at.date(),
            from_city=from_city,
            to_city=to_city,
            driver_name=driver_name,
            driver_number=driver_number,
            vehicle_number=vehicle_number,
        )
        sync_dispatch_entry(
            order,
            actor=actor,
            dispatched_at=dispatched_at,
            from_city=from_city,
            to_city=to_city,
            driver_name=driver_name,
            driver_number=driver_number,
            vehicle_number=vehicle_number,
            lot_numbers=lot_numbers,
            quantities=quantities,
        )
        update_order_status(order, StatusIds.DISPATCHED)
        rec.detail = dispatch_detail(order)
    notify_order_event(order, NotificationEvent.ORDER_DISPATCHED, actor=actor)
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

    assert_order_status(order, VERIFIABLE_STATUS_CODES, "verify")

    if not (admin is not None and (admin.is_admin_user or admin.is_superuser)):
        raise PermissionDenied("Orders can only be verified by a sales admin.")

    with recording(
        StockEventType.ORDER_CONFIRMED,
        StockEventDetail.ORDER_VERIFIED,
        order_product_ids(order),
        source=order,
        actor=admin,
    ):
        assert_products_usable(
            order_product_ids(order),
            field="status",
            action="be verified",
            subject="this order",
        )
        assert_stock_covers(InventoryOperations.order_bag_requirements(order), "verify")

        order.status = Status.by_id(StatusIds.CONFIRMED)
        order.verified_by = admin
        order.verified_at = indian_now()
        order.full_clean()
        order.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
    notify_order_event(order, NotificationEvent.ORDER_CONFIRMED, actor=admin)
    return order


@transaction.atomic
def unverify_order(
    order: Order, *, actor: User, status: StatusIds = StatusIds.UNDER_REVIEW
) -> Order:
    """Reverse a verification, clearing who verified it and when.

    The bags this order was holding are released automatically: reservations
    are derived from ``Order.status``, never stored.

    Lands in UNDER_REVIEW by default, which ``verify_order`` accepts -- so an
    order can go back and forth between approved and under review.
    """
    assert_order_status(order, UNVERIFIABLE_STATUS_CODES, "unverify")
    with recording(
        StockEventType.ORDER_RELEASED,
        StockEventDetail.UNVERIFIED,
        order_product_ids(order),
        source=order,
    ):
        order.status = Status.by_id(status)
        order.verified_by = None
        order.verified_at = None
        order.full_clean()
        order.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
    notify_order_event(order, NotificationEvent.ORDER_UNDER_REVIEW, actor=actor)
    return order


def revert_dispatch(order: Order, *, actor: User) -> Order:
    """Reverse a dispatch, returning the order to ``CONFIRMED``.

    Its bags move back from consumed to reserved on their own, for the same
    reason: both figures are derived from the status.

    The dispatch record stays attached -- it is what actually happened, and a
    re-dispatch overwrites it. Only the status is rewound.

    Only today's dispatch can be reverted (``assert_dispatched_today``). Note
    the knock-on: because a re-dispatch needs a revert first, re-dispatching is
    same-day only too.

    An order with a live return (PENDING or ACCEPTED) cannot be reverted: those
    goods are on the road back, and a REJECTED return does not count.
    """
    assert_order_status(order, REVERTIBLE_DISPATCH_STATUS_CODES, "revert the dispatch of")
    live_return = ReturnOrder.objects.filter(
        order=order, status_id__in=[int(s) for s in LIVE_RETURN_STATUS_IDS]
    ).first()
    if live_return is not None:
        raise ValidationError(
            {
                "status": (
                    f"Cannot revert the dispatch of an order with a live return "
                    f"({live_return.public_id}, {live_return.status.code}). "
                    "Reject or revert that return first."
                )
            }
        )
    assert_dispatched_today(order)
    with recording(
        StockEventType.DISPATCH_REVERTED,
        StockEventDetail.NONE,
        order_product_ids(order),
        source=order,
    ):
        order.status = Status.by_id(StatusIds.CONFIRMED)
        order.actual_delivery_date = None
        order.full_clean()
        order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    notify_order_event(order, NotificationEvent.ORDER_DISPATCH_REVERTED, actor=actor)
    return order


@transaction.atomic
def mark_delivered(order: Order, actual_delivery_date=None, *, actor: User) -> Order:
    """Mark a dispatched order delivered (refused while a product on it is not usable)."""
    assert_order_status(order, DELIVERABLE_STATUS_CODES, "deliver")
    assert_products_usable(
        order_product_ids(order), field="status", action="be delivered", subject="this order"
    )
    order.status = Status.by_id(StatusIds.DELIVERED)
    order.actual_delivery_date = actual_delivery_date or indian_now().date()
    order.full_clean()
    order.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    notify_order_event(order, NotificationEvent.ORDER_DELIVERED, actor=actor)
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
        "booked_for": child_org_payload(order.booked_for),
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


def order_export_payload(order: Order) -> dict:
    """:func:`order_payload` for the date-range export.

    Adds when the order was booked, the client's public id, and the city the
    order goes to (its own delivery address's city). Business fields only --
    no audit columns.
    """
    return {
        **order_payload(order),
        "created_at": order.created_at.isoformat(),
        "client": client_summary_payload(order.client),
        "city": order_city_payload(order),
    }


def order_list_payload(order: Order) -> dict:
    """Compact dict for the Android order list: one card per order.

    Narrower than :func:`order_payload` -- it carries what a list row shows
    (who, where, how much, what state) and summarises the lines instead of
    embedding the full packaging payload of each.

    Reads the item rows off the instance, so a ``prefetch_related("items")``
    whose queryset ``select_related("product_packaging__product")`` keeps this
    query-free -- ``packagings`` reaches through both relations.

    ``packagings`` is one entry per line: the **bag** that was ordered, how many
    of it, and the product it holds. The bag is the unit an order is placed in,
    so two sizes of the same seed are two entries here rather than one product
    listed twice.

    The nested ``product`` is :func:`ProductOperations.packaging_payload`'s,
    widened with the picture the card renders. ``packaging_payload`` itself is
    deliberately left alone: it is embedded in every order payload and across
    the sales-admin API, where the image does not belong -- the same reason
    ``catalogue_packaging_payload`` exists separately.
    """
    items = list(order.items.all())
    city = order.delivery_address.city if order.delivery_address_id else None
    return {
        "public_id": order.public_id,
        "created_at": order.created_at.isoformat(),
        "status": order.status.code if order.status_id else None,
        "client": {
            "public_id": order.client.public_id,
            "company_name": order.client.company_name,
        },
        "delivery_address": str(order.delivery_address),
        "city": {"id": city.id, "name": city.name} if city else None,
        "expected_delivery_date": order.expected_delivery_date.isoformat(),
        "dispatch_mode": "AGENCY" if order.transport_agency_id else "PRIVATE",
        "booked_for": child_org_summary_payload(order.booked_for),
        "total_amount": str(order.total_amount),
        "total_packets": order.total_packets,
        "item_count": len(items),
        "packagings": [
            {
                "negotiated_selling_price": str(item.negotiated_selling_price),
                **packaging_payload(item.product_packaging),
                "product": {
                    "public_id": item.product_packaging.product.public_id,
                    "name": item.product_packaging.product.name,
                    "image_url": item.product_packaging.product.image_url,
                },
                "quantity": item.quantity,
            }
            for item in items
        ],
    }


def order_detail_payload(order: Order) -> dict:
    """Full order detail: :func:`order_payload` with the client expanded.

    ``order_payload`` carries only ``{company_name, gst_number}`` for the
    client -- all the Android booking response needs. The sales-admin detail
    screen needs every address and transport agency *with its link id*, so the
    pickers on the edit screen can name one; that is exactly
    :func:`ClientOperations.client_payload`, which is a superset, so the key is
    replaced wholesale rather than merged.

    ``return_orders`` are all the order's live returns (PENDING or ACCEPTED) in
    full, newest first; a REJECTED return is hidden. ``return_order`` is the
    newest of them, or null -- deprecated, kept for the current web UI.
    """
    return {
        **order_payload(order),
        "client": client_payload(order.client),
        "return_order": order_return_payload(order),
        "return_orders": [return_order_payload(ret) for ret in live_return_orders(order)],
    }


ORDER_CORE_FIELDS = (
    "delivery_address",
    "transport_agency",
    "booked_for",
    "expected_delivery_date",
    "actual_delivery_date",
    "special_comments",
)

# ``special_comments`` accumulates rather than being replaced -- see
# :func:`appended_comment`. Every other core field is a plain overwrite.
APPEND_ONLY_ORDER_FIELDS = frozenset({"special_comments"})


def appended_comment(existing: str, addition: str) -> str:
    """``existing`` with ``addition`` added as a new line.

    Order comments are a running note, not a field: each one is a remark
    somebody made about this order, so a later remark must never erase an
    earlier one. A blank addition is a no-op rather than a blank line.
    """
    addition = addition.strip()
    if not addition:
        return existing
    return f"{existing}\n{addition}" if existing else addition


def update_order_core(order: Order, **fields) -> Order:
    """Update the admin-editable core of an order.

    ``client`` is **not** editable and is not a field here: an order belongs to
    the client it was booked for, and moving it would invalidate its delivery
    address, its transport agency and the prices its lines were negotiated at.

    ``created_by`` / ``created_at`` / ``verified_by`` / ``verified_at`` are not
    editable either: they are the audit record, and approval belongs to
    :func:`verify_order` alone.

    ``status`` is not editable here: every status change goes through its own
    lifecycle verb (:func:`verify_order`, :func:`unverify_order`,
    :func:`hold_order`, :func:`reject_order`, :func:`dispatch_order`,
    :func:`revert_dispatch`), which carries the guards and stock checks that
    move needs. Setting it here would skip them -- e.g. flipping CONFIRMED to
    BOOKED, raising quantities unchecked, and flipping back. An unknown field
    is a ``TypeError`` so such a call fails loudly rather than being dropped.

    ``special_comments`` is **appended to**, never replaced -- see
    :func:`appended_comment`.

    ``full_clean`` is what enforces the cross-field rules -- delivery address
    belongs to the client, transport agency is one of the client's own,
    CONFIRMED carries its verification details -- so they are not restated here.
    """
    unknown = set(fields) - set(ORDER_CORE_FIELDS)
    if unknown:
        raise TypeError(f"Not an editable order field: {', '.join(sorted(unknown))}.")

    for field in ORDER_CORE_FIELDS:
        if field not in fields:
            continue
        if field in APPEND_ONLY_ORDER_FIELDS:
            setattr(order, field, appended_comment(getattr(order, field), fields[field]))
        else:
            setattr(order, field, fields[field])
    order.full_clean()
    order.save()
    return order


@transaction.atomic
def sync_order_items(order: Order, items: list[dict], actor: User) -> list[OrderItem]:
    """Replace ``order``'s lines with ``items``, recording the stock it moves.

    See :func:`_sync_order_items` for the rules. Editing a CONFIRMED order
    moves reserved bags, which the stock ledger records as ``ORDER_EDITED``.
    """
    products = {
        item["product_packaging"].product_id
        for item in items
        if "product_packaging" in item
    }
    with recording(
        StockEventType.ORDER_EDITED,
        StockEventDetail.ORDER_LINES_CHANGED,
        order_product_ids(order, products),
        source=order,
        actor=actor,
    ):
        return _sync_order_items(order, items, actor)


def _sync_order_items(order: Order, items: list[dict], actor: User) -> list[OrderItem]:
    """Replace ``order``'s lines with ``items`` (full declarative replacement).

    Each entry is ``{"product_packaging", "quantity"}`` plus an optional
    ``"negotiated_selling_price"`` -- the same shape :func:`create_order` takes.
    A packaging not currently on the order is added, one already there is
    updated in place, and one the caller omits is removed. Lines are matched by
    ``product_packaging``: the natural key ``uniq_orderitem_order_packaging``
    already enforces.

    Existing lines are looked up through ``all_objects`` because that unique
    constraint is **not** soft-delete aware -- it covers removed rows too. A
    packaging that was taken off the order and later put back must therefore
    have its original row restored; inserting a second one would hit the
    constraint and surface as a 500 rather than a validation error.

    **A CONFIRMED order is re-checked against stock** before anything is
    written: its lines are reserved bags, so raising a quantity or adding a
    bag must be covered by what is available. The bags it already holds are
    credited back (``available_bags`` has netted them off), and a line that
    shrinks or stays put asks for nothing new -- see :func:`assert_stock_covers`.
    """
    if not items:
        raise ValidationError("An order must keep at least one item.")

    keys = [item["product_packaging"].pk for item in items]
    if len(set(keys)) != len(keys):
        raise ValidationError("The same product packaging is listed twice.")

    existing = {
        line.product_packaging_id: line
        for line in OrderItem.all_objects.filter(order=order).select_related(
            "product_packaging"
        )
    }

    # A frozen product's line may be removed or lowered (that releases stock) but
    # not added back or raised. A soft-deleted line being restored counts as added.
    assert_products_usable(
        {
            item["product_packaging"].product_id
            for item in items
            if existing.get(item["product_packaging"].pk) is None
            or existing[item["product_packaging"].pk].is_deleted
            or item["quantity"] > existing[item["product_packaging"].pk].quantity
        },
        field="items",
        action="have order lines added or raised",
        subject="this order",
    )

    if order.is_verified:
        held = {
            line.product_packaging: line.quantity
            for line in existing.values()
            if not line.is_deleted
        }
        needed = {item["product_packaging"]: item["quantity"] for item in items}
        assert_stock_covers(needed, "edit", held=held)

    ordered: list[OrderItem] = []
    for item in items:
        line = existing.pop(item["product_packaging"].pk, None)
        if line is None:
            line = add_order_item(
                order,
                product_packaging=item["product_packaging"],
                negotiated_selling_price=item.get("negotiated_selling_price"),
                quantity=item["quantity"],
                actor=actor,
            )
        else:
            line.restore()
            line.quantity = item["quantity"]
            if item.get("negotiated_selling_price") is not None:
                line.negotiated_selling_price = item["negotiated_selling_price"]
            line.full_clean()
            line.save()
        ordered.append(line)

    for stale in existing.values():
        stale.mark_deleted(actor)

    return ordered
