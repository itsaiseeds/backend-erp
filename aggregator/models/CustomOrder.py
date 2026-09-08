from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)

from .Order import (
    DISPATCH_REQUIRED_STATUS_CODES,
    ORDER_STATUS_CODES,
    default_expected_delivery_date,
)
from .Status import StatusIds


class CustomOrder(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A loose-packet order, made up of one or more ``CustomOrderItem`` rows.

    Unlike a normal :class:`Order`, a custom order draws on the **loose packet**
    pool of a packaging rather than sealed bags, so its lines are counted in
    packets. It is a standalone record -- there is deliberately **no** foreign key
    to ``Order``; it mirrors the same required fields except for its line items.

    Created only by a sales admin (``created_by``) -- a salesperson cannot book
    one. It shares the order lifecycle statuses and the same dispatch rules: at
    most one of ``dispatch_details`` / ``private_dispatch_details`` may be set,
    and exactly one is required once the order is dispatched.

    Exposed to the frontend by its ``public_id`` (``CORD-…``); the primary key
    is never sent out.
    """

    public_id_prefix = "CORD-"

    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="custom_orders",
    )
    delivery_address = models.ForeignKey(
        "aggregator.Address",
        verbose_name="delivery address",
        on_delete=models.PROTECT,
        related_name="custom_orders",
    )
    status = models.ForeignKey(
        "aggregator.Status",
        verbose_name="status",
        on_delete=models.PROTECT,
        related_name="custom_orders",
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
        related_name="custom_orders",
    )
    private_dispatch_details = models.ForeignKey(
        "aggregator.PrivateDispatchDetails",
        verbose_name="private dispatch details",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="custom_orders",
    )
    special_comments = models.TextField("special comments", blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="verified by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Sales admin who verified this custom order.",
    )
    verified_at = models.DateTimeField("verified at", null=True, blank=True)

    class Meta:
        verbose_name = "custom order"
        verbose_name_plural = "custom orders"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(
                    dispatch_details__isnull=False,
                    private_dispatch_details__isnull=False,
                ),
                name="ck_customorder_not_both_dispatch_details",
            ),
        ]

    def __str__(self):
        return self.public_id or "Custom order"

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), 0)

    @property
    def total_packets(self):
        """Total loose packets across all lines (lines are already counted in packets)."""
        return sum((item.packets for item in self.items.all()), 0)

    @property
    def is_verified(self):
        return bool(self.status_id and self.status.code == StatusIds.CONFIRMED.name)

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
            errors["status"] = "Invalid status for a custom order."

        if (
            self.status_id
            and self.status.code == StatusIds.CONFIRMED.name
            and (self.verified_by_id is None or self.verified_at is None)
        ):
            errors["status"] = "A verified custom order must record who verified it and when."

        if self.verified_by_id and not (
            self.verified_by.is_admin_user or self.verified_by.is_superuser
        ):
            errors["verified_by"] = "Custom orders can only be verified by a sales admin."

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
                "A custom order cannot have both dispatch details and private "
                "dispatch details."
            )

        if (
            self.status_id
            and self.status.code in DISPATCH_REQUIRED_STATUS_CODES
            and not self.dispatch_details_id
            and not self.private_dispatch_details_id
        ):
            errors["status"] = (
                "Dispatch details are required once the custom order is dispatched."
            )

        # A custom order is an admin instrument: only a sales admin (or a
        # superuser) may book one -- never a salesperson.
        if self.created_by_id and not (
            self.created_by.is_admin_user or self.created_by.is_superuser
        ):
            errors["created_by"] = "Custom orders can only be created by a sales admin."

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
