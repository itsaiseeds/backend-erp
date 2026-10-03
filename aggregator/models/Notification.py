from django.conf import settings
from django.db import models

from common.models import TimeStampedModel

from .Order import Order


class Notification(TimeStampedModel):
    """An in-app inbox entry, written whether or not the push reaches the phone.

    Saved in the same transaction as the change it reports, so a rolled-back
    change leaves no notification behind.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="recipient",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_type = models.CharField("event type", max_length=32)
    title = models.CharField("title", max_length=120)
    body = models.CharField("body", max_length=255)
    data = models.JSONField(
        "data",
        default=dict,
        blank=True,
        help_text="What the target screen needs, e.g. {'order_public_id': 'ORD-...'}.",
    )
    order = models.ForeignKey(
        Order,
        verbose_name="order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    read_at = models.DateTimeField("read at", null=True, blank=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"], name="ix_notification_recipient"),
        ]

    def __str__(self):
        return f"{self.recipient_id}: {self.title}"
