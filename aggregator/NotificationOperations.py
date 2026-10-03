"""Notifications for the sales person whose work an admin just acted on.

Order status changes, a client being verified and a return being accepted or
rejected each call a ``notify_*_event`` function, which hands the whole job --
saving the in-app :class:`~aggregator.models.Notification` row and pushing it to
the recipient's phones -- to ``fire_and_forget``. It therefore runs only once the
change has committed (a rolled-back change notifies nobody), off the request
thread, and a failure anywhere in it is logged and swallowed rather than failing
the change.

Every notification is one ``event`` (what happened), which fixes its title, its
wording and the app ``screen`` to open; the ids that screen needs travel in
``data``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from django.utils import timezone

from common.background import fire_and_forget
from common.push import send_push

from .models import Client, Notification, Order, PushDevice, ReturnOrder


class NotificationEvent(StrEnum):
    """What happened; the value is stored as ``Notification.event_type``."""

    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_UNDER_REVIEW = "ORDER_UNDER_REVIEW"
    ORDER_ON_HOLD = "ORDER_ON_HOLD"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_DISPATCHED = "ORDER_DISPATCHED"
    ORDER_DISPATCH_REVERTED = "ORDER_DISPATCH_REVERTED"
    ORDER_DELIVERED = "ORDER_DELIVERED"
    CLIENT_VERIFIED = "CLIENT_VERIFIED"
    RETURN_ACCEPTED = "RETURN_ACCEPTED"
    RETURN_REJECTED = "RETURN_REJECTED"


class Screen(StrEnum):
    """The app screen a notification opens; the value is the route name the app maps."""

    ORDER_DETAIL = "order_detail"
    CLIENT_DETAIL = "client_detail"
    RETURN_ORDER_DETAIL = "return_order_detail"


@dataclass(frozen=True)
class EventSpec:
    """Per-event wording and destination: the body is "<subject> <outcome>."."""

    title: str
    outcome: str
    screen: Screen


_E = NotificationEvent
_SPECS: dict[NotificationEvent, EventSpec] = {
    _E.ORDER_CONFIRMED: EventSpec("Order confirmed", "was confirmed", Screen.ORDER_DETAIL),
    _E.ORDER_UNDER_REVIEW: EventSpec(
        "Order under review", "is back under review", Screen.ORDER_DETAIL
    ),
    _E.ORDER_ON_HOLD: EventSpec("Order on hold", "was put on hold", Screen.ORDER_DETAIL),
    _E.ORDER_REJECTED: EventSpec("Order rejected", "was rejected", Screen.ORDER_DETAIL),
    _E.ORDER_DISPATCHED: EventSpec("Order dispatched", "has been dispatched", Screen.ORDER_DETAIL),
    _E.ORDER_DISPATCH_REVERTED: EventSpec(
        "Dispatch reverted", "had its dispatch reverted", Screen.ORDER_DETAIL
    ),
    _E.ORDER_DELIVERED: EventSpec("Order delivered", "has been delivered", Screen.ORDER_DETAIL),
    _E.CLIENT_VERIFIED: EventSpec("Client verified", "was verified", Screen.CLIENT_DETAIL),
    _E.RETURN_ACCEPTED: EventSpec("Return accepted", "was accepted", Screen.RETURN_ORDER_DETAIL),
    _E.RETURN_REJECTED: EventSpec("Return rejected", "was rejected", Screen.RETURN_ORDER_DETAIL),
}


@dataclass(frozen=True)
class Message:
    """What one notification is about and to whom; ``recipient_id`` None means nobody."""

    recipient_id: int | None
    subject: str
    data: dict[str, str]
    order_id: int | None = None


def notify_order_event(order: Order, event: NotificationEvent) -> None:
    """Tell the order's booking sales person that ``order`` just changed."""
    order_id = order.pk
    _notify(event, lambda: _order_message(order_id))


def notify_client_event(client: Client, event: NotificationEvent) -> None:
    """Tell the sales person who onboarded ``client`` what an admin did with it."""
    client_id = client.pk
    _notify(event, lambda: _client_message(client_id))


def notify_return_order_event(ret: ReturnOrder, event: NotificationEvent) -> None:
    """Tell the sales person who raised ``ret`` what an admin decided."""
    return_id = ret.pk
    _notify(event, lambda: _return_order_message(return_id))


def _notify(event: NotificationEvent, build: Callable[[], Message]) -> None:
    """Queue the notification: it runs after commit, off the request thread.

    A notification that breaks must never break the change that triggered it, so
    nothing here -- not even loading the subject -- happens before the queue.
    """
    fire_and_forget(lambda: deliver_event(event, build))


def _order_message(order_id: int) -> Message:
    order = Order.objects.select_related("client").get(pk=order_id)
    return Message(
        recipient_id=order.created_by_id,
        subject=f"{order.public_id} for {order.client.company_name}",
        data={"order_public_id": order.public_id},
        order_id=order.pk,
    )


def _client_message(client_id: int) -> Message:
    client = Client.objects.get(pk=client_id)
    return Message(
        recipient_id=client.created_by_id,
        subject=client.company_name,
        data={"client_public_id": client.public_id},
    )


def _return_order_message(return_id: int) -> Message:
    ret = ReturnOrder.objects.select_related("order__client").get(pk=return_id)
    order = ret.order
    return Message(
        recipient_id=ret.created_by_id,
        subject=f"{ret.public_id} against {order.public_id} for {order.client.company_name}",
        data={"return_order_public_id": ret.public_id, "order_public_id": order.public_id},
        order_id=order.pk,
    )


def deliver_event(event: NotificationEvent, build: Callable[[], Message]) -> Notification | None:
    """Save the inbox row for ``event`` and push it; ``None`` when nobody is to be told."""
    message = build()
    if message.recipient_id is None:
        return None

    spec = _SPECS[event]
    body = f"{message.subject} {spec.outcome}."
    notification = Notification.objects.create(
        recipient_id=message.recipient_id,
        event_type=event.value,
        title=spec.title,
        body=body,
        data=message.data,
        order_id=message.order_id,
    )
    # FCM data values must be strings, so the screen's data travels as a JSON string.
    push = {
        "type": event.value,
        "screen": spec.screen.value,
        "notification_id": str(notification.pk),
        "data": json.dumps(notification.data),
    }
    push_to_user(message.recipient_id, spec.title, body, push)
    return notification


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
