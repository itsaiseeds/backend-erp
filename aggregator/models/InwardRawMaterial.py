from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)

from .InwardEntryMixin import InwardEntryMixin
from .Status import StatusIds
from .StockEvent import StockEventDetail, StockEventType


class InwardRawMaterialStatus(models.TextChoices):
    """Lifecycle of an inward raw-material lot.

    ``LAB_TESTING`` rows are held back from stock until the lab signs off;
    the user flips the status to ``IN_USE`` when the material is usable, or to
    ``REJECTED`` when the lab fails it. ``LAB_TESTING`` is the hub: both other
    statuses are only ever reached from it, and only ever revert back to it
    (see ``InwardOperations.ALLOWED_RAW_STATUS_TRANSITIONS`` --
    ``IN_USE <-> REJECTED`` is never a direct move). This is a display-only
    enum: the ``status`` field itself is a foreign key to ``aggregator.Status``,
    and each member's ``name`` here is exactly the ``code`` of its seeded row
    (see ``StatusIds.raw_material_statuses``) -- note ``REJECTED`` here seeds
    under the distinct code ``RAW_MATERIAL_REJECTED``, not the unrelated
    order-lifecycle ``REJECTED`` status.
    """

    LAB_TESTING = "Lab Testing", "Lab Testing"
    IN_USE = "In Use", "In Use"
    # Member name is RAW_MATERIAL_REJECTED (not REJECTED) because
    # raw_status_of()/status_row_for() resolve a Status row by this enum's
    # .name as the seeded `code` -- and `code` is unique, so this cannot
    # collide with the unrelated order-lifecycle Status row seeded under the
    # code 'REJECTED' (StatusIds.REJECTED = 7). The *value* (what the API
    # sends/receives) and the label are still plain "Rejected".
    RAW_MATERIAL_REJECTED = "Rejected", "Rejected"


class InwardRawMaterial(
    InwardEntryMixin,
    PrefixedPublicIdModel,
    TimeStampedModel,
    SoftDeletedModel,
    CreatedByModel,
):
    """Inward movement of raw material (product replenishment).

    A new stock lot for a ``Product``: how many kilograms came in, from which
    ``Party``, under which supplier batch number (``lot_no``), when it was
    sampled for the lab, and its ``status``. The entry's date is
    ``created_at``; flipping ``status`` to ``IN_USE`` or ``REJECTED`` stamps
    ``effective_date`` with today, and once reached the lot counts toward
    usable or rejected stock respectively. Reverting either to
    ``LAB_TESTING`` clears ``effective_date`` and re-stamps
    ``lab_sampling_date`` with today, as if the lot were freshly back with the
    lab.

    ``lot_no`` is the supplier's own batch number printed on the consignment --
    free text, required at booking, unrelated to the per-line lot number
    captured at dispatch.

    Exposed to the frontend by its ``public_id`` (``IR-…``).
    """

    public_id_prefix = "IR-"

    lab_sampling_date = models.DateField(
        "lab sampling date",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="inward_raw_materials",
    )
    quantity_kg = models.DecimalField(
        "quantity in kg",
        max_digits=10,
        decimal_places=3,
    )
    lot_no = models.CharField(
        "lot number",
        max_length=64,
        help_text="The supplier's own batch number for this consignment.",
    )
    status = models.ForeignKey(
        "aggregator.Status",
        verbose_name="status",
        on_delete=models.PROTECT,
        default=StatusIds.LAB_TESTING.value,
        related_name="inward_raw_materials",
    )

    class Meta:
        verbose_name = "inward raw material"
        verbose_name_plural = "inward raw materials"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_kg__gte=0),
                name="ck_inwardrawmaterial_quantity_kg_non_negative",
            ),
        ]

    def guard_soft_delete(self, perform):
        """Refuse removing kilograms already packed into bags or loose packets.

        ``InwardOperations.assert_raw_lot_removable`` is the rule (and its
        message is what the API has always answered), checked under the
        product's raw-pool lock so a concurrent count cannot slip between.
        """
        from django.core.exceptions import ValidationError

        from aggregator import InventoryOperations, InwardOperations, StockLedgerOperations
        from aggregator.ProductOperations import assert_products_usable

        self.refuse_return_lot_change()
        with StockLedgerOperations.recording(
            StockEventType.INWARD_OPERATIONS,
            StockEventDetail.RAW_LOT_DELETED,
            [self.product_id],
            source=self,
        ) as rec:
            assert_products_usable([self.product_id], action="have its inward lot deleted")
            InventoryOperations.lock_raw_pools([self.product_id])
            try:
                InwardOperations.assert_raw_lot_removable(self)
            except ValueError as exc:
                raise ValidationError(str(exc)) from None
            perform()
            rec.actor = self.deleted_by

    def __str__(self):
        return f"{self.public_id}: {self.product} {self.quantity_kg} kg"
