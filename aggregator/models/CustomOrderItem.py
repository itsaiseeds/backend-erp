from decimal import ROUND_HALF_UP, Decimal

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

    A **waste order** (``CustomOrder.made_from_waste``) carries *kg lines*
    instead: ``quantity_kg`` set, ``packet_weight`` and ``packets`` null, drawn
    from the product's waste pool. Exactly one of the two shapes
    (``ck_customorderitem_one_kind``).
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
        "negotiated selling price per packet (per kg on a kg line)",
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Per-packet price for this line (per kg on a waste order's kg line). "
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
        null=True,
        blank=True,
        help_text=(
            "Weight of a single packet on this line, in kilograms. Selects "
            "which loose-stock pool the line draws from. Null on a kg line."
        ),
    )
    packets = models.PositiveIntegerField("packets", null=True, blank=True)
    quantity_kg = models.DecimalField(
        "quantity kg",
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Kilograms of waste on a waste order's line. Null on a packet line.",
    )

    class Meta:
        verbose_name = "custom order item"
        verbose_name_plural = "custom order items"
        ordering = ["custom_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["custom_order", "product", "packet_weight"],
                name="uniq_customorderitem_order_product_weight",
            ),
            models.UniqueConstraint(
                fields=["custom_order", "product"],
                condition=models.Q(packet_weight__isnull=True),
                name="uniq_customorderitem_order_product_kg",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        packet_weight__isnull=False,
                        packets__isnull=False,
                        quantity_kg__isnull=True,
                    )
                    | models.Q(
                        packet_weight__isnull=True,
                        packets__isnull=True,
                        quantity_kg__isnull=False,
                    )
                ),
                name="ck_customorderitem_one_kind",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(negotiated_selling_price__gte=0)
                    & (models.Q(packets__isnull=True) | models.Q(packets__gt=0))
                    & (
                        models.Q(packet_weight__isnull=True)
                        | models.Q(packet_weight__gt=0)
                    )
                    & (
                        models.Q(quantity_kg__isnull=True)
                        | models.Q(quantity_kg__gt=0)
                    )
                ),
                name="ck_customorderitem_positive",
            ),
        ]

    def __str__(self):
        if self.product_id and self.is_kg_line:
            return f"{self.quantity_kg}kg {self.product.name}"
        if self.product_id:
            return f"{self.packets} × {self.packet_weight}kg {self.product.name}"
        return "custom order item"

    @property
    def is_kg_line(self):
        """True on a waste order's line, which is counted in kg rather than packets."""
        return self.quantity_kg is not None

    @property
    def line_total(self):
        """Price x kg on a kg line (rounded to paise), price x packets on a packet line."""
        if self.is_kg_line:
            return (self.negotiated_selling_price * self.quantity_kg).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        return self.negotiated_selling_price * self.packets
