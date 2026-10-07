from django.db import models

from authentication.validators import validate_phone_number
from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class PartyType(models.TextChoices):
    """What a party supplies: raw material lots or other (packing) material lots.

    A raw-material lot may only be booked against a ``RAW_MATERIAL`` party and
    an other-material lot only against an ``OTHER_MATERIAL`` one (see
    ``InwardOperations.assert_party_type``). A plain string enum, not a lookup FK.
    """

    RAW_MATERIAL = "RAW_MATERIAL", "Raw Material"
    OTHER_MATERIAL = "OTHER_MATERIAL", "Other Material"


class Party(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A supplier/party that inward materials (raw or other) come from.

    Merges the party's name, city and (optional) contact number. Lookup
    master data, referenced by both inward tables by ``Party`` FK; not
    exposed to a frontend by a public id (like ``City``).
    """

    name = models.CharField("name", max_length=255)
    city = models.ForeignKey(
        "aggregator.City",
        verbose_name="city",
        on_delete=models.PROTECT,
        related_name="parties",
    )
    party_type = models.CharField(
        "party type",
        max_length=32,
        choices=PartyType.choices,
        help_text="What this party supplies (raw material or other material).",
    )
    contact_number = models.CharField(
        "contact number",
        max_length=10,
        blank=True,
        null=True,
        validators=[validate_phone_number],
    )

    class Meta:
        verbose_name = "party"
        verbose_name_plural = "parties"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "city"],
                name="uniq_party_name_city",
            ),
            models.CheckConstraint(
                condition=models.Q(party_type__in=PartyType.values),
                name="ck_party_party_type",
            ),
        ]

    def __str__(self):
        return self.name
