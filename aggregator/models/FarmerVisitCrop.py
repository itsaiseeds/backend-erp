from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class FarmerVisitCrop(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A crop the farmer of a ``FarmerVisit`` grows (link table)."""

    farmer_visit = models.ForeignKey(
        "aggregator.FarmerVisit",
        verbose_name="farmer visit",
        on_delete=models.PROTECT,
        related_name="visit_crops",
    )
    crop = models.ForeignKey(
        "aggregator.Crop",
        verbose_name="crop",
        on_delete=models.PROTECT,
        related_name="farmer_visit_crops",
    )

    class Meta:
        verbose_name = "farmer visit crop"
        verbose_name_plural = "farmer visit crops"
        ordering = ["farmer_visit", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["farmer_visit", "crop"],
                name="uniq_farmervisitcrop_visit_crop",
            ),
        ]

    def __str__(self):
        return f"{self.farmer_visit_id} grows {self.crop_id}"
