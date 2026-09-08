from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class CustomOrderItem(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A single line on a ``CustomOrder``: raw ``Product`` packets at a per-packet price.

    A custom order deliberately bypasses packaging entirely -- it deals in the
    raw product and a plain packet count, drawn from the product's loose-packet pool.
    There is no ``ProductPackaging`` here on purpose: that is what separates a
    custom order from a normal ``OrderItem`` (which sells sealed packagings).
    """

    custom_order = models.ForeignKey(
        "aggregator.CustomOrder",
        verbose_name="custom order",
        on_delete=models.PROTECT,
        related_name="items",
    )
    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="custom_order_items",
    )
    negotiated_selling_price = models.DecimalField(
        "negotiated selling price per packet",
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Per-packet price for this line (loose packets are priced per packet, matching "
            "Product.selling_price's unit). ``CustomOrderOperations.add_custom_order_item`` "
            "defaults it to the product's per-packet selling_price when omitted."
        ),
    )
    packets = models.PositiveIntegerField("packets")

    class Meta:
        verbose_name = "custom order item"
        verbose_name_plural = "custom order items"
        ordering = ["custom_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["custom_order", "product"],
                name="uniq_customorderitem_order_product",
            ),
            models.CheckConstraint(
                condition=models.Q(negotiated_selling_price__gte=0) & models.Q(packets__gt=0),
                name="ck_customorderitem_positive",
            ),
        ]

    def __str__(self):
        if self.product_id:
            return f"{self.packets} packets × {self.product.name}"
        return "custom order item"

    @property
    def line_total(self):
        return self.negotiated_selling_price * self.packets
