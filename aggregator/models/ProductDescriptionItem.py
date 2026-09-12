from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class ProductDescriptionItem(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """One marketing bullet on a ``Product`` ("Ripes in 80 to 85 days").

    The rows of a product make up the feature list the Android catalogue renders
    under the product card. They are never addressed on their own -- like
    ``Address``, the model carries no ``public_id``; the whole list is written at
    once through ``ProductOperations.sync_product_description_items`` and read
    back as an ordered list of strings.
    """

    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="description_items",
    )
    text = models.CharField("text", max_length=255)
    sequence = models.PositiveSmallIntegerField(
        "sequence",
        default=0,
        help_text="Display order within the product's feature list (0-based).",
    )

    class Meta:
        verbose_name = "product description item"
        verbose_name_plural = "product description items"
        ordering = ["sequence", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "text"],
                name="uniq_productdescriptionitem_product_text",
            ),
        ]

    def __str__(self):
        return self.text
