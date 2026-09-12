from django.core.exceptions import ValidationError
from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)

from .InventorySnapshot import default_snapshot_date


class LooseStockSnapshot(
    PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel
):
    """Loose packets counted for one ``(product, packet_weight)`` on one date.

    "Loose" does not mean unpacked -- it means stock that is **in a packet but
    not in a bag**. Such a packet is identified entirely by its product and its
    weight: which ``ProductPackaging`` it would have been bagged into is not a
    property it has. A product with a 1kg x 20 and a 1kg x 30 packaging has one
    pool of loose 1kg packets, not two.

    That is why this table keys on ``(product, packet_weight)`` and carries no
    packaging foreign key. ``ProductPackaging.packets`` describes how many
    packets go *in a bag* and is meaningless here.

    Unlike ``InventorySnapshot``, recording this count is **optional**: it is
    excluded from ``is_stock_count_complete``, so a missing loose count never
    blocks order verification. The two tables therefore run on **independent
    date lifecycles** -- each purge touches only its own table, and a bag count
    for a new day must never delete a loose count that is still accurate.
    Because of that, loose figures are read at the latest *loose* snapshot date
    rather than today (see ``InventoryOperations.loose_date``).

    Exposed to the frontend by its ``public_id`` (``LS-...``); the primary key is
    never sent out.
    """

    public_id_prefix = "LS-"

    snapshot_date = models.DateField(
        "snapshot date",
        default=default_snapshot_date,
        db_index=True,
    )
    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="loose_stock_snapshots",
    )
    packet_weight = models.DecimalField(
        "packet weight",
        max_digits=8,
        decimal_places=3,
        help_text="Weight of a single loose packet, in kilograms.",
    )
    packets = models.PositiveIntegerField(
        "packets",
        help_text=(
            "Loose packets of this product at this packet weight. Consumed only "
            "by custom orders -- a packaged order may never draw from here."
        ),
    )

    class Meta:
        verbose_name = "loose stock snapshot"
        verbose_name_plural = "loose stock snapshots"
        ordering = ["-snapshot_date", "product__name", "packet_weight"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot_date", "product", "packet_weight"],
                name="uniq_loosestocksnapshot_date_product_weight",
            ),
            models.CheckConstraint(
                condition=models.Q(packet_weight__gt=0),
                name="ck_loosestocksnapshot_positive",
            ),
        ]

    def __str__(self):
        if self.product_id:
            return (
                f"{self.snapshot_date}: {self.packets} x "
                f"{self.packet_weight}kg {self.product.name}"
            )
        return f"loose stock snapshot {self.snapshot_date}"

    @property
    def total_weight(self):
        """Total physical weight of the loose packets, in kilograms."""
        return self.packets * self.packet_weight

    def clean(self):
        super().clean()
        errors = {}

        # ``can_update_stock_count`` gates exactly one thing: writing a stock
        # count. It deliberately does not gate order verification.
        if self.created_by_id and not self.created_by.is_superuser:
            admin = getattr(self.created_by, "admin_profile", None)
            if admin is None:
                errors["created_by"] = (
                    "Stock counts can only be recorded by a sales admin."
                )
            elif not admin.can_update_stock_count:
                errors["created_by"] = (
                    "This admin is not allowed to update the stock count."
                )

        if errors:
            raise ValidationError(errors)
