from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
    indian_now,
)

from .StockEvent import StockEventDetail, StockEventType


class RawMaterialWaste(
    PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel
):
    """Raw material of a ``Product`` written off as wasted (spoiled, spilled, ...).

    Each live row takes ``quantity_kg`` out of the product's unpacked raw pool
    -- see ``InventoryOperations.raw_wasted_kg`` -- so it is no longer
    available to pack. There is deliberately **no date**: waste is a standing
    deduction, not a dated movement, and is always counted.

    A wrong entry is fixed by editing it (``update_raw_waste``) or soft-deleting
    it, which gives the kilograms back.

    Exposed to the frontend by its ``public_id`` (``WS-…``).
    """

    public_id_prefix = "WS-"

    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="raw_material_wastes",
    )
    quantity_kg = models.DecimalField(
        "quantity in kg",
        max_digits=10,
        decimal_places=3,
        help_text="Kilograms of raw material wasted.",
    )
    reason = models.CharField(
        "reason",
        max_length=255,
        blank=True,
        default="",
        help_text="Why it was wasted (free text).",
    )

    inward_raw_material = models.ForeignKey(
        "aggregator.InwardRawMaterial",
        verbose_name="source rejected lot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="waste_entries",
        help_text=(
            "Set when this row writes off a whole lab-rejected lot "
            "(``InventoryOperations.convert_rejected_lot_to_waste``)."
        ),
    )

    class Meta:
        verbose_name = "raw material waste"
        verbose_name_plural = "raw material wastes"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_kg__gt=0),
                name="ck_rawmaterialwaste_quantity_kg_positive",
            ),
            models.UniqueConstraint(
                fields=["inward_raw_material"],
                condition=models.Q(is_deleted=False, inward_raw_material__isnull=False),
                name="uq_rawmaterialwaste_live_lot",
            ),
        ]

    def guard_soft_delete(self, perform):
        """Delete the waste row, recording the kilograms it gives back."""
        from aggregator import InventoryOperations, StockLedgerOperations
        from aggregator.ProductOperations import assert_products_usable

        from .InwardRawMaterial import InwardRawMaterial
        from .Status import StatusIds

        if self.inward_raw_material_id is not None:
            with StockLedgerOperations.recording(
                StockEventType.WASTE_TO_REJECTED,
                StockEventDetail.NONE,
                [self.product_id],
                source=self,
            ) as rec:
                assert_products_usable(
                    [self.product_id], action="restore this lot to rejected"
                )
                InventoryOperations.lock_rejected_lots([self.inward_raw_material_id])
                InventoryOperations.lock_waste_pools([self.product_id])
                perform()
                InventoryOperations.assert_waste_available([self.product_id])
                # The lot goes back to the rejected stock it was converted from.
                InwardRawMaterial.all_objects.filter(pk=self.inward_raw_material_id).update(
                    status_id=StatusIds.RAW_MATERIAL_REJECTED.value, updated_at=indian_now()
                )
                rec.actor = self.deleted_by
            return

        with StockLedgerOperations.recording(
            StockEventType.RAW_WASTED,
            StockEventDetail.WASTE_DELETED,
            [self.product_id],
            source=self,
        ) as rec:
            assert_products_usable([self.product_id], action="have its waste entry deleted")
            InventoryOperations.lock_waste_pools([self.product_id])
            perform()
            # Waste already sold on a waste order cannot be taken away.
            InventoryOperations.assert_waste_available([self.product_id])
            rec.actor = self.deleted_by

    def __str__(self):
        return f"{self.public_id}: {self.product} {self.quantity_kg} kg wasted"
