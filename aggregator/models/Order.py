from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
    indian_now,
)

ORDER_STATUS_CODES = {
    "BOOKED",
    "UNDER_REVIEW",
    "CONFIRMED",
    "DISPATCHED",
    "DELIVERED",
    "ON_HOLD",
    "REJECTED",
}
DISPATCH_REQUIRED_STATUS_CODES = {"DISPATCHED", "DELIVERED"}


def default_expected_delivery_date():
    """Default expected delivery: the day after the order is booked."""
    return indian_now().date() + timedelta(days=1)


class Order(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A booked order for a client, made up of one or more ``OrderItem`` rows.

    Booked by a sales person (``created_by``). Dispatch details are attached
    later: at most one of ``dispatch_details`` / ``private_dispatch_details``
    may ever be set, and exactly one is required once the order is dispatched.

    Exposed to the frontend by its ``public_id`` (``ORD-…``); the primary key is
    never sent out.
    """

    public_id_prefix = "ORD-"

    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    delivery_address = models.ForeignKey(
        "aggregator.Address",
        verbose_name="delivery address",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.ForeignKey(
        "aggregator.Status",
        verbose_name="status",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    expected_delivery_date = models.DateField(
        "expected delivery date",
        default=default_expected_delivery_date,
    )
    actual_delivery_date = models.DateField(
        "actual delivery date",
        null=True,
        blank=True,
    )
    dispatch_details = models.ForeignKey(
        "aggregator.DispatchDetails",
        verbose_name="dispatch details",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    private_dispatch_details = models.ForeignKey(
        "aggregator.PrivateDispatchDetails",
        verbose_name="private dispatch details",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    special_comments = models.TextField("special comments", blank=True)

    class Meta:
        verbose_name = "order"
        verbose_name_plural = "orders"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(
                    dispatch_details__isnull=False,
                    private_dispatch_details__isnull=False,
                ),
                name="ck_order_not_both_dispatch_details",
            ),
        ]

    def __str__(self):
        return self.public_id or "Order"

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), 0)

    @property
    def total_bags(self):
        return sum(
            (
                item.quantity * item.product_packaging.packing_bags
                for item in self.items.all()
            ),
            0,
        )

    @property
    def is_dispatched(self):
        return bool(self.status_id and self.status.code in DISPATCH_REQUIRED_STATUS_CODES)

    @property
    def active_dispatch(self):
        if self.dispatch_details_id:
            return self.dispatch_details
        if self.private_dispatch_details_id:
            return self.private_dispatch_details
        return None

    def clean(self):
        super().clean()
        errors = {}

        if self.status_id and self.status.code not in ORDER_STATUS_CODES:
            errors["status"] = "Invalid status for an order."

        if self.client_id and self.delivery_address_id:
            from .ClientAddress import ClientAddress

            belongs = ClientAddress.objects.filter(
                client_id=self.client_id,
                address_id=self.delivery_address_id,
            ).exists()
            if not belongs:
                errors["delivery_address"] = (
                    "Delivery address must belong to the selected client."
                )

        if self.dispatch_details_id and self.private_dispatch_details_id:
            errors["dispatch_details"] = (
                "An order cannot have both dispatch details and private dispatch details."
            )

        if (
            self.status_id
            and self.status.code in DISPATCH_REQUIRED_STATUS_CODES
            and not self.dispatch_details_id
            and not self.private_dispatch_details_id
        ):
            errors["status"] = "Dispatch details are required once the order is dispatched."

        if self.created_by_id and not self.created_by.is_salesperson:
            errors["created_by"] = "Orders can only be created by a sales person."

        if self.client_id:
            if self.dispatch_details_id and self.dispatch_details.client_id != self.client_id:
                errors["dispatch_details"] = "Dispatch details belong to a different client."
            if (
                self.private_dispatch_details_id
                and self.private_dispatch_details.client_id != self.client_id
            ):
                errors["private_dispatch_details"] = (
                    "Dispatch details belong to a different client."
                )

        if errors:
            raise ValidationError(errors)
