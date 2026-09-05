from django.db import models

from authentication.validators import validate_phone_number
from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class Contact(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A contact person (name + phone). Not necessarily a system user."""

    name = models.CharField("name", max_length=255)
    phone_number = models.CharField(
        "phone number",
        max_length=10,
        validators=[validate_phone_number],
    )

    class Meta:
        verbose_name = "contact"
        verbose_name_plural = "contacts"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "phone_number"],
                name="uniq_contact_name_phone",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone_number})"
