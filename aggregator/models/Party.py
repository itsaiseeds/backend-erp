from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class Party(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A supplier/party that inward materials (raw or other) come from.

    Merges the party's name and city. Lookup master data, referenced by both
    inward tables by ``Party`` FK; not exposed to a frontend by a public id
    (like ``City``).
    """

    name = models.CharField("name", max_length=255)
    city = models.ForeignKey(
        "aggregator.City",
        verbose_name="city",
        on_delete=models.PROTECT,
        related_name="parties",
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
        ]

    def __str__(self):
        return self.name
