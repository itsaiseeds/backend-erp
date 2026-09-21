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
    """The sealed bags counted for one ``ProductPackaging`` on one date.

    This table holds **one pool only**: ``bags``, sealed whole packagings, the
    unit ``OrderItem.quantity`` is expressed in. Normal packaged orders draw
    from here and from nowhere else.

    The other pool -- stock that is in a packet but not in a bag -- lives in
    ``LooseStockSnapshot``, keyed by ``(product, packet_weight)``. It is a
    separate table because a loose packet has no packaging: ``packets``
    describes how many packets go *in a bag*, which says nothing about a packet
    sitting outside one. The two pools never mix, and they run on independent
    date lifecycles.

    Moving stock between the pools is a physical act: the admin opens a bag on
    the floor, then re-uploads this count (``bags - 1``) and the loose count
    (``packets + N``). Both tables stay pure records of what was counted -- they
    carry no synthetic movements.

    Only the latest ``snapshot_date`` is retained; recording a count for a newer
    date hard-deletes every earlier row (see
    ``aggregator.InventoryOperations.record_stock_counts``). That purge is
    scoped to this table and never touches loose stock.

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
    def total_packets(self):
        """Packets held inside the sealed bags."""
        return self.bags * self.product_packaging.packets

    @property
    def total_weight(self):
        """Total physical weight of the sealed bags, in kilograms."""
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
