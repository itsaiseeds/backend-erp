from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)


class Product(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A product we buy and sell, priced per bag.

    Exposed to the frontend by its ``public_id`` (``P-…``); the primary key is
    never sent out.
    """

    public_id_prefix = "P-"

    name = models.CharField("name", max_length=255)
    crop = models.ForeignKey(
        "aggregator.Crop",
        verbose_name="crop",
        on_delete=models.PROTECT,
        related_name="products",
    )
    buying_price = models.DecimalField(
        "buying price per bag",
        max_digits=12,
        decimal_places=2,
    )
    selling_price = models.DecimalField(
        "selling price per bag",
        max_digits=12,
        decimal_places=2,
    )

    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "crop"],
                name="uniq_product_name_crop",
            ),
            models.CheckConstraint(
                condition=models.Q(buying_price__gte=0) & models.Q(selling_price__gte=0),
                name="ck_product_prices_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.crop})" if self.crop_id else self.name

    @property
    def margin_per_bag(self):
        return self.selling_price - self.buying_price
