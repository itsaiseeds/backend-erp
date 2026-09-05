from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from authentication.validators import validate_phone_number
from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel

from ..validators import validate_gst_number
from .Status import StatusIds

CLIENT_STATUS_CODES = {s.name for s in StatusIds.client_statuses()}


class Client(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A customer company we sell to.

    Created by a sales person (``created_by``) and later verified by a sales
    admin. Its addresses, contacts and transport agencies are attached through
    the ``ClientAddress`` / ``ClientContact`` / ``ClientTransportAgency`` link
    tables.
    """

    company_name = models.CharField("company name", max_length=255)
    company_phone = models.CharField(
        "company phone",
        max_length=10,
        blank=True,
        validators=[validate_phone_number],
    )
    gst_number = models.CharField(
        "GST number",
        max_length=15,
        unique=True,
        validators=[validate_gst_number],
    )
    status = models.ForeignKey(
        "aggregator.Status",
        verbose_name="status",
        on_delete=models.PROTECT,
        related_name="clients",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="verified by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Sales admin who verified this client.",
    )
    verified_at = models.DateTimeField("verified at", null=True, blank=True)

    class Meta:
        verbose_name = "client"
        verbose_name_plural = "clients"
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name

    @property
    def addresses(self):
        """The client's addresses, reached through the link table."""
        from .Address import Address

        return Address.objects.filter(client_addresses__client=self)

    @property
    def contacts(self):
        from .Contact import Contact

        return Contact.objects.filter(client_contacts__client=self)

    @property
    def transport_agencies(self):
        from .TransportAgency import TransportAgency

        return TransportAgency.objects.filter(client_transport_agencies__client=self)

    @property
    def primary_address(self):
        link = self.client_addresses.filter(is_primary=True).first()
        return link.address if link else None

    @property
    def primary_contact(self):
        link = self.client_contacts.filter(is_primary=True).first()
        return link.contact if link else None

    @property
    def is_verified(self):
        return (
            self.status.code == StatusIds.VERIFIED.name if self.status_id else False
        )

    def clean(self):
        super().clean()
        errors = {}

        if self.gst_number:
            self.gst_number = self.gst_number.strip().upper()

        if self.created_by_id and not self.created_by.is_salesperson:
            errors["created_by"] = "Clients can only be created by a sales person."

        if self.status_id:
            if self.status.code not in CLIENT_STATUS_CODES:
                errors["status"] = "Invalid status for a client."
            elif self.status.code == StatusIds.VERIFIED.name:
                if self.verified_by_id is None or self.verified_at is None:
                    errors["status"] = (
                        "A verified client must record who verified it and when."
                    )
            elif (
                self.status.code == StatusIds.VERIFICATION_PENDING.name
                and self.verified_by_id
            ):
                errors["verified_by"] = (
                    "A pending client cannot have verification details."
                )

        if self.verified_by_id and not (
            self.verified_by.is_admin_user or self.verified_by.is_superuser
        ):
            errors["verified_by"] = "Clients can only be verified by a sales admin."

        if errors:
            raise ValidationError(errors)
