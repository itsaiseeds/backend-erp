from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class Country(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A country. Root of the geographic master-data hierarchy."""

    name = models.CharField("name", max_length=255, unique=True, db_index=True)
    iso_code = models.CharField(
        "ISO code",
        max_length=3,
        unique=True,
        db_index=True,
        help_text="ISO 3166 country code, e.g. 'IN' or 'IND'.",
    )

    class Meta:
        verbose_name = "country"
        verbose_name_plural = "countries"
        ordering = ["name"]

    def __str__(self):
        return self.name
