from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)


class ProductPackaging(
    PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel
):
    """A packaging variant of a ``Product`` (bag weight × number of bags).

    Exposed to the frontend by its ``public_id`` (``PP-…``); the primary key is
    never sent out.
    """

    public_id_prefix = "PP-"

    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="packagings",
    )
    packing_bag_weight = models.DecimalField(
        "packing bag weight",
        max_digits=8,
        decimal_places=3,
        help_text="Weight of a single bag, in kilograms.",
    )
    packing_bags = models.PositiveIntegerField("packing bags")

    class Meta:
        verbose_name = "product packaging"
        verbose_name_plural = "product packagings"
        ordering = ["product__name", "packing_bag_weight"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "packing_bag_weight", "packing_bags"],
                name="uniq_productpackaging_product_weight_bags",
            ),
            models.CheckConstraint(
                condition=models.Q(packing_bag_weight__gt=0) & models.Q(packing_bags__gt=0),
                name="ck_productpackaging_positive",
            ),
        ]

    def __str__(self):
        if self.product_id:
            return f"{self.product.name}: {self.packing_bags} × {self.packing_bag_weight}kg"
        return "product packaging"

    @property
    def total_weight(self):
        return self.packing_bag_weight * self.packing_bags
