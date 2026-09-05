from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class ClientContact(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """Links a ``Client`` to one of its ``Contact`` people."""

    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="client_contacts",
    )
    contact = models.ForeignKey(
        "aggregator.Contact",
        verbose_name="contact",
        on_delete=models.PROTECT,
        related_name="client_contacts",
    )
    role = models.CharField(
        "role",
        max_length=64,
        blank=True,
        help_text="e.g. 'Owner', 'Accountant'.",
    )
    is_primary = models.BooleanField("is primary", default=False)

    class Meta:
        verbose_name = "client contact"
        verbose_name_plural = "client contacts"
        ordering = ["-is_primary", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "contact"],
                name="uniq_clientcontact_client_contact",
            ),
            models.UniqueConstraint(
                fields=["client"],
                condition=models.Q(is_primary=True, is_deleted=False),
                name="uniq_clientcontact_one_primary",
            ),
        ]

    def __str__(self):
        return f"{self.client} → {self.contact}" if self.client_id else "client contact"
