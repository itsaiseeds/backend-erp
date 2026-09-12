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
    """A packaging variant of a ``Product`` (packet weight × number of packets).

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
    packet_weight = models.DecimalField(
        "packet weight",
        max_digits=8,
        decimal_places=3,
        help_text="Weight of a single packet, in kilograms.",
    )
    packets = models.PositiveIntegerField("packets")
    selling_price = models.DecimalField(
        "selling price",
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Whole-packaging price (not per-packet). Downstream OrderItems default "
            "their negotiated price to this value. Set explicitly, or leave to "
            "ProductOperations.add_packaging which fills it with "
            "packets * product.price_for_weight(packet_weight). Frozen at the value stored "
            "here -- it does not track later changes to the product's per-kilogram rate."
        ),
    )

    class Meta:
        verbose_name = "product packaging"
        verbose_name_plural = "product packagings"
        ordering = ["product__name", "packet_weight"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "packet_weight", "packets"],
                name="uniq_productpackaging_product_weight_packets",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(packet_weight__gt=0)
                    & models.Q(packets__gt=0)
                    & models.Q(selling_price__gte=0)
                ),
                name="ck_productpackaging_positive",
            ),
        ]

    def __str__(self):
        if self.product_id:
            return f"{self.product.name}: {self.packets} × {self.packet_weight}kg"
        return "product packaging"

    @property
    def total_weight(self):
        return self.packet_weight * self.packets
