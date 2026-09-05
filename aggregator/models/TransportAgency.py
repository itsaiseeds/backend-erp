from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class TransportAgency(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A transport agency, identified only by its name."""

    name = models.CharField("name", max_length=255)

    class Meta:
        verbose_name = "transport agency"
        verbose_name_plural = "transport agencies"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="uniq_transportagency_name",
            ),
        ]

    def __str__(self):
        return self.name
