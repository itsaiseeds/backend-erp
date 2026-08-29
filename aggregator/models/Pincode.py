from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class Pincode(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A postal/pin code, tied to a city."""

    code = models.CharField("code", max_length=10, db_index=True)
    city = models.ForeignKey(
        "aggregator.City",
        verbose_name="city",
        on_delete=models.PROTECT,
        related_name="pincodes",
    )

    class Meta:
        verbose_name = "pincode"
        verbose_name_plural = "pincodes"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["city", "code"],
                name="uniq_pincode_city_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} – {self.city}" if self.city_id else self.code

    @property
    def state(self):
        """State of this pincode, reached through its city (may be None)."""
        if self.city_id is None:
            return None
        return self.city.state

    @property
    def country(self):
        """Country of this pincode, reached through its city (may be None)."""
        if self.city_id is None:
            return None
        return self.city.country
