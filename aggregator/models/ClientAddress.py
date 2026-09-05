from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class ClientAddress(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """Links a ``Client`` to one of its ``Address`` rows."""

    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="client_addresses",
    )
    address = models.ForeignKey(
        "aggregator.Address",
        verbose_name="address",
        on_delete=models.PROTECT,
        related_name="client_addresses",
    )
    label = models.CharField(
        "label",
        max_length=64,
        blank=True,
        help_text="e.g. 'Warehouse', 'Billing'.",
    )
    is_primary = models.BooleanField("is primary", default=False)

    class Meta:
        verbose_name = "client address"
        verbose_name_plural = "client addresses"
        ordering = ["-is_primary", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "address"],
                name="uniq_clientaddress_client_address",
            ),
            models.UniqueConstraint(
                fields=["client"],
                condition=models.Q(is_primary=True, is_deleted=False),
                name="uniq_clientaddress_one_primary",
            ),
        ]

    def __str__(self):
        return f"{self.client} → {self.address}" if self.client_id else "client address"
