from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class City(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A city or town inside a state."""

    name = models.CharField("name", max_length=255)
    state = models.ForeignKey(
        "aggregator.State",
        verbose_name="state",
        on_delete=models.PROTECT,
        related_name="cities",
    )

    class Meta:
        verbose_name = "city"
        verbose_name_plural = "cities"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["state", "name"],
                name="uniq_city_state_name",
            ),
        ]

    def __str__(self):
        return f"{self.name}, {self.state}" if self.state_id else self.name

    @property
    def country(self):
        """Country of this city, reached through its state (may be None)."""
        if self.state_id is None:
            return None
        return self.state.country
