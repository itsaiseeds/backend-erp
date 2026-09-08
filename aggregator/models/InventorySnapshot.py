from django.core.exceptions import ValidationError
from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
    indian_now,
)


def default_snapshot_date():
    """Default snapshot date: today in the project's timezone (Asia/Kolkata)."""
    return indian_now().date()


class InventorySnapshot(
    PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel
):
    """The physical stock counted for one ``ProductPackaging`` on one date.

    Stock is held in two pools that never mix:

    * ``bags``    - sealed whole packagings, the unit ``OrderItem.quantity``
      is expressed in. Normal packaged orders draw from here.
    * ``loose_packets`` - unpacked single packets. Optional (defaults to 0); reserved
      for the future custom-order flow, which may never break open a bag.

    Moving stock between the pools is a physical act: the admin opens bags on
    the floor and re-uploads the count (``bags - 1``, ``loose_packets + N``).
    This table therefore stays a pure record of what was counted -- it carries no
    synthetic movements.

    Only the latest ``snapshot_date`` is retained; recording a count for a newer
    date hard-deletes every earlier row (see
    ``aggregator.InventoryOperations.record_stock_counts``).

    Exposed to the frontend by its ``public_id`` (``INV-…``); the primary key is
    never sent out.
    """

    public_id_prefix = "INV-"

    snapshot_date = models.DateField(
        "snapshot date",
        default=default_snapshot_date,
        db_index=True,
    )
    product_packaging = models.ForeignKey(
        "aggregator.ProductPackaging",
        verbose_name="product packaging",
        on_delete=models.PROTECT,
        related_name="inventory_snapshots",
    )
    bags = models.PositiveIntegerField(
        "bags",
        help_text=(
            "Sealed whole packaging on hand. Comparable directly against "
            "OrderItem.quantity. May be 0 when only loose stock is held."
        ),
    )
    loose_packets = models.PositiveIntegerField(
        "loose packets",
        default=0,
        help_text=(
            "Unpacked single packets on hand, in the packaging's packet size. "
            "Optional -- defaults to 0. Never consumed by a packaged order."
        ),
    )

    class Meta:
        verbose_name = "inventory snapshot"
        verbose_name_plural = "inventory snapshots"
        ordering = ["-snapshot_date", "product_packaging__product__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot_date", "product_packaging"],
                name="uniq_inventorysnapshot_date_packaging",
            ),
        ]

    def __str__(self):
        if self.product_packaging_id:
            return f"{self.snapshot_date}: {self.bags} × {self.product_packaging}"
        return f"inventory snapshot {self.snapshot_date}"

    @property
    def bag_packets(self):
        """Packets held inside the sealed bags."""
        return self.bags * self.product_packaging.packets

    @property
    def total_packets(self):
        """Every packet on hand, sealed and loose."""
        return self.bag_packets + self.loose_packets

    @property
    def total_weight(self):
        """Total physical weight on hand, in kilograms."""
        return self.total_packets * self.product_packaging.packet_weight

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
