from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class CustomOrderItem(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A single line on a ``CustomOrder``: loose packets of one product at one weight.

    A custom order deliberately bypasses packaging entirely -- it deals in the
    raw product, a packet weight and a plain packet count, drawn from the
    matching ``LooseStockSnapshot`` pool. There is no ``ProductPackaging`` here
    on purpose: that is what separates a custom order from a normal
    ``OrderItem`` (which sells sealed bags).

    ``packet_weight`` is required because a loose packet has a definite weight:
    5 x 1kg and 5 x 500g draw on different pools and are worth different money.
    One order may therefore carry a 1kg line and a 500g line of the same
    product, which is what the uniqueness constraint allows for.
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
            "Per-packet price for this line. "
            "``CustomOrderOperations.add_custom_order_item`` defaults it to "
            "``product.price_for_weight(packet_weight)`` -- the product's "
            "per-kilogram rate applied to this line's packet weight, so a 500g "
            "line and a 1kg line prefill different, correct prices."
        ),
    )
    packet_weight = models.DecimalField(
        "packet weight",
        max_digits=8,
        decimal_places=3,
        help_text=(
            "Weight of a single packet on this line, in kilograms. Selects "
            "which loose-stock pool the line draws from."
        ),
    )
    packets = models.PositiveIntegerField("packets")

    class Meta:
        verbose_name = "custom order item"
        verbose_name_plural = "custom order items"
        ordering = ["custom_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["custom_order", "product", "packet_weight"],
                name="uniq_customorderitem_order_product_weight",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(negotiated_selling_price__gte=0)
                    & models.Q(packets__gt=0)
                    & models.Q(packet_weight__gt=0)
                ),
                name="ck_customorderitem_positive",
            ),
        ]

    def __str__(self):
        if self.product_id:
            return f"{self.packets} × {self.packet_weight}kg {self.product.name}"
        return "custom order item"

    @property
    def line_total(self):
        return self.negotiated_selling_price * self.packets
