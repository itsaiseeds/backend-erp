from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class OrderItem(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A single line on an ``Order``: a packaging at a negotiated price."""

    order = models.ForeignKey(
        "aggregator.Order",
        verbose_name="order",
        on_delete=models.PROTECT,
        related_name="items",
    )
    product_packaging = models.ForeignKey(
        "aggregator.ProductPackaging",
        verbose_name="product packaging",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    negotiated_selling_price = models.DecimalField(
        "negotiated selling price per packaging",
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Whole-packaging price for this line (matches ProductPackaging.selling_price's "
            "unit, not the product's per-bag price). ``OrderOperations.add_order_item`` "
            "defaults it to the linked ``ProductPackaging.selling_price`` when omitted."
        ),
    )
    quantity = models.PositiveIntegerField("quantity")

    class Meta:
        verbose_name = "order item"
        verbose_name_plural = "order items"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product_packaging"],
                name="uniq_orderitem_order_packaging",
            ),
            models.CheckConstraint(
                condition=models.Q(negotiated_selling_price__gte=0) & models.Q(quantity__gt=0),
                name="ck_orderitem_positive",
            ),
        ]

    def __str__(self):
        if self.product_packaging_id:
            return f"{self.quantity} × {self.product_packaging}"
        return "order item"

    @property
    def line_total(self):
        return self.negotiated_selling_price * self.quantity
