from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
    indian_now,
)

from .Status import StatusIds

RETURN_STATUS_CODES = {s.name for s in StatusIds.return_statuses()}
# A return is *live* while PENDING or ACCEPTED: it counts toward the order's
# returnable limit. An order may carry any number of live returns (their sum
# stays within the challan; docs/prd/multiple-return-orders.md). A REJECTED
# return is kept for the record but is out of the way.
LIVE_RETURN_STATUS_IDS = (StatusIds.RETURN_PENDING, StatusIds.RETURN_ACCEPTED)


def today_ist():
    """Default ``return_date``: today in IST."""
    return indian_now().date()


class ReturnOrder(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """Goods a client sent back against an order that was already shipped.

    Raised by the sales person who booked the order (``created_by``), made up of
    one or more ``ReturnOrderItem`` rows, and accepted or rejected by a sales
    admin. An ACCEPTED return is inward stock: ``ReturnOrderOperations`` books
    ``InwardRawMaterial`` / ``InwardOtherMaterial`` rows that point back here.

    ``include_in_other_raw_materials`` is null until the return is accepted, and
    records the admin's choice then: whether the packing materials went back into
    stock too.

    Exposed to the frontend by its ``public_id`` (``RET-…``).
    """

    public_id_prefix = "RET-"

    order = models.ForeignKey(
        "aggregator.Order",
        verbose_name="order",
        on_delete=models.PROTECT,
        related_name="return_orders",
    )
    status = models.ForeignKey(
        "aggregator.Status",
        verbose_name="status",
        on_delete=models.PROTECT,
        related_name="return_orders",
    )
    return_date = models.DateField(
        "return date",
        default=today_ist,
        help_text="Informational only; the inward stock is dated by the accept day.",
    )
    include_in_other_raw_materials = models.BooleanField(
        "include in other raw materials",
        null=True,
        blank=True,
        help_text="Set on accept: whether the packing materials were booked back too.",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="verified by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Sales admin who accepted this return.",
    )
    verified_at = models.DateTimeField("verified at", null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="rejected by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Sales admin who rejected this return.",
    )
    rejected_at = models.DateTimeField("rejected at", null=True, blank=True)

    class Meta:
        verbose_name = "return order"
        verbose_name_plural = "return orders"
        ordering = ["-created_at"]

    def __str__(self):
        return self.public_id or "Return order"

    @property
    def total_kg(self):
        return sum((item.kg for item in self.items.all()), 0)

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), 0)

    @property
    def is_pending(self):
        return self.status_id == StatusIds.RETURN_PENDING

    def clean(self):
        super().clean()
        errors = {}

        if self.status_id and self.status.code not in RETURN_STATUS_CODES:
            errors["status"] = "Invalid status for a return order."

        if self.status_id == StatusIds.RETURN_ACCEPTED and (
            self.verified_by_id is None or self.verified_at is None
        ):
            errors["status"] = "An accepted return must record who accepted it and when."

        if self.status_id == StatusIds.RETURN_REJECTED and (
            self.rejected_by_id is None or self.rejected_at is None
        ):
            errors["status"] = "A rejected return must record who rejected it and when."

        for field in ("verified_by", "rejected_by"):
            user = getattr(self, field)
            if user is not None and not (user.is_admin_user or user.is_superuser):
                errors[field] = "Returns can only be accepted or rejected by a sales admin."

        if self.created_by_id and not self.created_by.is_salesperson:
            errors["created_by"] = "Returns can only be raised by a sales person."

        if errors:
            raise ValidationError(errors)
