from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class ReturnOrderItem(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """One returned line: packets of a ``(product, packet_weight)`` at a price.

    A line names the product and packet weight rather than a ``ProductPackaging``
    because stock comes back as loose packets, not bags. The returnable limit is
    the packets on the order's challan (``DispatchEntryItem.quantity`` x
    ``packaging.packets``) for the same pair.
    """

    return_order = models.ForeignKey(
        "aggregator.ReturnOrder",
        verbose_name="return order",
        on_delete=models.PROTECT,
        related_name="items",
    )
    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="return_order_items",
    )
    packet_weight = models.DecimalField(
        "packet weight",
        max_digits=8,
        decimal_places=3,
        help_text="Weight of one returned packet, in kilograms.",
    )
    packets = models.PositiveIntegerField("packets")
    price_per_packet = models.DecimalField(
        "price per packet",
        max_digits=12,
        decimal_places=2,
        help_text="Entered by the sales person; the GET prefill suggests the order's rate.",
    )

    class Meta:
        verbose_name = "return order item"
        verbose_name_plural = "return order items"
        ordering = ["return_order", "id"]
        constraints = [
            # Not soft-delete aware, like uniq_orderitem_order_packaging: syncing
            # items restores a removed row instead of inserting a second one.
            models.UniqueConstraint(
                fields=["return_order", "product", "packet_weight"],
                name="uniq_returnorderitem_return_product_weight",
            ),
            models.CheckConstraint(
                condition=models.Q(packets__gt=0) & models.Q(price_per_packet__gte=0),
                name="ck_returnorderitem_positive",
            ),
        ]

    def __str__(self):
        if self.product_id:
            return f"{self.packets} × {self.packet_weight}kg {self.product}"
        return "return order item"

    @property
    def kg(self):
        return self.packet_weight * self.packets

    @property
    def line_total(self):
        return self.price_per_packet * self.packets
