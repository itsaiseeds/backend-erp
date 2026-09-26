from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)

from .InwardEntryMixin import InwardEntryMixin


class InwardRawMaterialStatus(models.TextChoices):
    """Lifecycle of an inward raw-material lot.

    ``LAB_TESTING`` rows are held back from stock until the lab signs off;
    the user flips the status to ``IN_USE`` when the material is usable.
    """

    LAB_TESTING = "Lab Testing", "Lab Testing"
    IN_USE = "In Use", "In Use"


class InwardRawMaterial(
    InwardEntryMixin,
    PrefixedPublicIdModel,
    TimeStampedModel,
    SoftDeletedModel,
    CreatedByModel,
):
    """Inward movement of raw material (product replenishment).

    A new stock lot for a ``Product``: how many kilograms came in, from which
    ``Party``, when it was sampled for the lab, and its ``status``. The entry's
    date is ``created_at``; flipping ``status`` to ``IN_USE`` stamps
    ``effective_date`` with today, and once reached the lot counts toward stock.
    Reverting to ``LAB_TESTING`` clears the date and stops the count.

    Exposed to the frontend by its ``public_id`` (``IR-…``).
    """

    public_id_prefix = "IR-"

    lab_sampling_date = models.DateField(
        "lab sampling date",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="inward_raw_materials",
    )
    quantity_kg = models.DecimalField(
        "quantity in kg",
        max_digits=10,
        decimal_places=3,
    )
    status = models.CharField(
        "status",
        max_length=16,
        choices=InwardRawMaterialStatus.choices,
        default=InwardRawMaterialStatus.LAB_TESTING,
        db_index=True,
    )

    class Meta:
        verbose_name = "inward raw material"
        verbose_name_plural = "inward raw materials"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_kg__gte=0),
                name="ck_inwardrawmaterial_quantity_kg_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.public_id}: {self.product} {self.quantity_kg} kg"
