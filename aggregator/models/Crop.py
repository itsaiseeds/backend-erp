from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class Crop(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A crop that products belong to (master data)."""

    name = models.CharField("name", max_length=255)

    class Meta:
        verbose_name = "crop"
        verbose_name_plural = "crops"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="uniq_crop_name",
            ),
        ]

    def __str__(self):
        return self.name
