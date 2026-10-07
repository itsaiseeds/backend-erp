"""Notifications for the sales person whose work an admin just acted on, and for
the lab testers when a raw-material lot needs testing.

Order status changes, a field trip being approved or un-approved, a client being
verified and a return being accepted or rejected each call a ``notify_*_event``
function, which hands the whole job -- saving the in-app
:class:`~aggregator.models.Notification` row and pushing it to the recipient's
phones -- to ``fire_and_forget``. It therefore runs only once the change has
committed (a rolled-back change notifies nobody), off the request thread, and a
failure anywhere in it is logged and swallowed rather than failing the change.

Every notification is one ``event`` (what happened), which fixes its title, its
wording and the app ``screen`` to open; the ids that screen needs travel in
``data``. The body names **who did it** -- "... was confirmed by Asha Rao." --
because a sales person reading "was confirmed" cannot otherwise tell an admin's
decision from anything else that might have moved the order, and the actor's
name is snapshotted into the stored text at the moment of the change.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from django.utils import timezone

from authentication.models import LabTester
from common.background import fire_and_forget
from common.push import send_push

from .models import (
    Client,
    FieldTrip,
    InwardRawMaterial,
    Notification,
    Order,
    PushDevice,
    ReturnOrder,
)

if TYPE_CHECKING:
    from authentication.models import User


class NotificationEvent(StrEnum):
    """What happened; the value is stored as ``Notification.event_type``."""

    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_UNDER_REVIEW = "ORDER_UNDER_REVIEW"
    ORDER_ON_HOLD = "ORDER_ON_HOLD"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_DISPATCHED = "ORDER_DISPATCHED"
    ORDER_DISPATCH_REVERTED = "ORDER_DISPATCH_REVERTED"
    ORDER_DELIVERED = "ORDER_DELIVERED"
    FIELD_TRIP_APPROVED = "FIELD_TRIP_APPROVED"
    FIELD_TRIP_UNAPPROVED = "FIELD_TRIP_UNAPPROVED"
    CLIENT_VERIFIED = "CLIENT_VERIFIED"
    RETURN_ACCEPTED = "RETURN_ACCEPTED"
    RETURN_REJECTED = "RETURN_REJECTED"
    LAB_TEST_REQUESTED = "LAB_TEST_REQUESTED"


class Screen(StrEnum):
    """The app screen a notification opens; the value is the route name the app maps."""

    ORDER_DETAIL = "order_detail"
    FIELD_TRIP_DETAIL = "field_trip_detail"
    CLIENT_DETAIL = "client_detail"
    RETURN_ORDER_DETAIL = "return_order_detail"
    LAB_TEST_PENDING = "lab_test_pending"


@dataclass(frozen=True)
class EventSpec:
    """Per-event wording and destination.

    ``outcome`` is a verb phrase that reads on after its subject and before the
    actor's name -- "was confirmed", "has been dispatched" -- so every event
    shares the body "<subject> <outcome> by <actor>."
    """

    title: str
    outcome: str
    screen: Screen


_E = NotificationEvent
_SPECS: dict[NotificationEvent, EventSpec] = {
    _E.ORDER_CONFIRMED: EventSpec("Order confirmed", "was confirmed", Screen.ORDER_DETAIL),
    _E.ORDER_UNDER_REVIEW: EventSpec(
        "Order under review", "was sent back under review", Screen.ORDER_DETAIL
    ),
    _E.ORDER_ON_HOLD: EventSpec("Order on hold", "was put on hold", Screen.ORDER_DETAIL),
    _E.ORDER_REJECTED: EventSpec("Order rejected", "was rejected", Screen.ORDER_DETAIL),
    _E.ORDER_DISPATCHED: EventSpec("Order dispatched", "has been dispatched", Screen.ORDER_DETAIL),
    _E.ORDER_DISPATCH_REVERTED: EventSpec(
        "Dispatch reverted", "had its dispatch reverted", Screen.ORDER_DETAIL
    ),
    _E.ORDER_DELIVERED: EventSpec("Order delivered", "has been delivered", Screen.ORDER_DETAIL),
    _E.FIELD_TRIP_APPROVED: EventSpec(
        "Field trip approved", "was approved", Screen.FIELD_TRIP_DETAIL
    ),
    _E.FIELD_TRIP_UNAPPROVED: EventSpec(
        "Field trip approval withdrawn",
        "had its approval withdrawn",
        Screen.FIELD_TRIP_DETAIL,
    ),
    _E.CLIENT_VERIFIED: EventSpec("Client verified", "was verified", Screen.CLIENT_DETAIL),
    _E.RETURN_ACCEPTED: EventSpec("Return accepted", "was accepted", Screen.RETURN_ORDER_DETAIL),
    _E.RETURN_REJECTED: EventSpec("Return rejected", "was rejected", Screen.RETURN_ORDER_DETAIL),
    _E.LAB_TEST_REQUESTED: EventSpec(
        "Lab test requested", "was sent for lab testing", Screen.LAB_TEST_PENDING
    ),
}


@dataclass(frozen=True)
class Message:
    """What one notification is about and to whom; no ``recipient_ids`` means nobody."""

    recipient_ids: tuple[int, ...]
    subject: str
    data: dict[str, str]
    order_id: int | None = None


def notify_order_event(order: Order, event: NotificationEvent, *, actor: User) -> None:
    """Tell the order's booking sales person that ``order`` just changed by ``actor``."""
    order_id = order.pk
    _notify(event, actor, lambda: _order_message(order_id))


def notify_field_trip_event(trip: FieldTrip, event: NotificationEvent, *, actor: User) -> None:
    """Tell the sales person who planned ``trip`` what ``actor`` decided about it."""
    trip_id = trip.pk
    _notify(event, actor, lambda: _field_trip_message(trip_id))


def notify_client_event(client: Client, event: NotificationEvent, *, actor: User) -> None:
    """Tell the sales person who onboarded ``client`` what ``actor`` did with it."""
    client_id = client.pk
    _notify(event, actor, lambda: _client_message(client_id))


def notify_return_order_event(ret: ReturnOrder, event: NotificationEvent, *, actor: User) -> None:
    """Tell the sales person who raised ``ret`` what ``actor`` decided."""
    return_id = ret.pk
    _notify(event, actor, lambda: _return_order_message(return_id))


def notify_lab_test_requested(lot: InwardRawMaterial, *, actor: User) -> None:
    """Tell every lab tester that ``lot`` is waiting in Lab Testing (booked, or sent back)."""
    lot_id = lot.pk
    _notify(NotificationEvent.LAB_TEST_REQUESTED, actor, lambda: _lab_test_message(lot_id))


def _only(user_id: int | None) -> tuple[int, ...]:
    """A single recipient as ``Message.recipient_ids``; none when there is no user."""
    return () if user_id is None else (user_id,)


def _notify(event: NotificationEvent, actor: User, build: Callable[[], Message]) -> None:
    """Queue the notification: it runs after commit, off the request thread.

    A notification that breaks must never break the change that triggered it, so
    nothing here -- not even loading the subject, or reading the actor's name --
    happens before the queue.
    """
    fire_and_forget(lambda: deliver_event(event, actor.display_name, build))


def _order_message(order_id: int) -> Message:
    order = Order.objects.select_related("client").get(pk=order_id)
    return Message(
        recipient_ids=_only(order.created_by_id),
        subject=f"{order.public_id} for {order.client.company_name}",
        data={"order_public_id": order.public_id},
        order_id=order.pk,
    )


def _field_trip_message(trip_id: int) -> Message:
    trip = FieldTrip.objects.get(pk=trip_id)
    return Message(
        recipient_ids=_only(trip.created_by_id),
        subject=f"{trip.public_id} to {trip.village}",
        data={"field_trip_public_id": trip.public_id},
    )


def _client_message(client_id: int) -> Message:
    client = Client.objects.get(pk=client_id)
    return Message(
        recipient_ids=_only(client.created_by_id),
        subject=client.company_name,
        data={"client_public_id": client.public_id},
    )


def _return_order_message(return_id: int) -> Message:
    ret = ReturnOrder.objects.select_related("order__client").get(pk=return_id)
    order = ret.order
    return Message(
        recipient_ids=_only(ret.created_by_id),
        subject=f"{ret.public_id} against {order.public_id} for {order.client.company_name}",
        data={"return_order_public_id": ret.public_id, "order_public_id": order.public_id},
        order_id=order.pk,
    )


def _lab_test_message(lot_id: int) -> Message:
    lot = InwardRawMaterial.objects.select_related("product").get(pk=lot_id)
    testers = LabTester.objects.order_by("user_id").values_list("user_id", flat=True)
    return Message(
        recipient_ids=tuple(testers),
        subject=f"{lot.public_id} ({lot.product.name}, {lot.quantity_kg} kg)",
        data={"inward_raw_material_public_id": lot.public_id},
    )


def deliver_event(
    event: NotificationEvent, actor_name: str, build: Callable[[], Message]
) -> Notification | None:
    """Save an inbox row per recipient of ``event`` and push each; the first row, or
    ``None`` when nobody is to be told."""
    message = build()
    spec = _SPECS[event]
    body = f"{message.subject} {spec.outcome} by {actor_name}."
    first: Notification | None = None
    for recipient_id in message.recipient_ids:
        notification = Notification.objects.create(
            recipient_id=recipient_id,
            event_type=event.value,
            title=spec.title,
            body=body,
            data=message.data,
            order_id=message.order_id,
        )
        first = first or notification
        # FCM data values must be strings, so the screen's data travels as a JSON string.
        push = {
            "type": event.value,
            "screen": spec.screen.value,
            "notification_id": str(notification.pk),
            "data": json.dumps(notification.data),
        }
        push_to_user(recipient_id, spec.title, body, push)
    return first


def push_to_user(user_id: int, title: str, body: str, data: dict[str, str]) -> None:
    """Push to every phone ``user_id`` is signed in on; forget tokens FCM says are dead."""
    tokens = list(PushDevice.objects.filter(user_id=user_id).values_list("fcm_token", flat=True))
    dead = send_push(tokens, title, body, data)
    if dead:
        PushDevice.objects.filter(fcm_token__in=dead).delete()


def register_device(user_id: int, fcm_token: str, app_version: str) -> PushDevice:
    """Attach ``fcm_token`` to ``user_id``, moving it off whoever held it before."""
    device, _ = PushDevice.objects.update_or_create(
        fcm_token=fcm_token,
        defaults={"user_id": user_id, "app_version": app_version},
    )
    return device


def mark_read(user_id: int, notification_id: int | None = None) -> int:
    """Mark one of ``user_id``'s notifications (or all) read; return how many changed."""
    unread = Notification.objects.filter(recipient_id=user_id, read_at__isnull=True)
    if notification_id is not None:
        unread = unread.filter(pk=notification_id)
    return unread.update(read_at=timezone.now(), updated_at=timezone.now())


def notification_payload(notification: Notification) -> dict[str, object]:
    return {
        "id": notification.pk,
        "event_type": notification.event_type,
        "title": notification.title,
        "body": notification.body,
        "screen": _SPECS[NotificationEvent(notification.event_type)].screen.value,
        "data": notification.data,
        "is_read": notification.read_at is not None,
        "created_at": notification.created_at,
    }
