from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class FarmerVisitProduct(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A product of ours the farmer of a ``FarmerVisit`` uses (link table).

    No rows for a visit means the farmer does not use our products.
    """

    farmer_visit = models.ForeignKey(
        "aggregator.FarmerVisit",
        verbose_name="farmer visit",
        on_delete=models.PROTECT,
        related_name="visit_products",
    )
    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="farmer_visit_products",
    )

    class Meta:
        verbose_name = "farmer visit product"
        verbose_name_plural = "farmer visit products"
        ordering = ["farmer_visit", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["farmer_visit", "product"],
                name="uniq_farmervisitproduct_visit_product",
            ),
        ]

    def __str__(self):
        return f"{self.farmer_visit_id} uses {self.product_id}"
