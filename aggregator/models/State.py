from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class State(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A state or province inside a country."""

    name = models.CharField("name", max_length=255)
    code = models.CharField(
        "code",
        max_length=10,
        blank=True,
        null=True,
        help_text="Short abbreviation, e.g. 'MH' for Maharashtra.",
    )
    country = models.ForeignKey(
        "aggregator.Country",
        verbose_name="country",
        on_delete=models.PROTECT,
        related_name="states",
    )

    class Meta:
        verbose_name = "state"
        verbose_name_plural = "states"
        ordering = ["country__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "name"],
                name="uniq_state_country_name",
            ),
        ]

    def __str__(self):
        return f"{self.name}, {self.country}" if self.country_id else self.name
