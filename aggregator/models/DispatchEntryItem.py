from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class DispatchEntryItem(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A single line of a ``DispatchEntry``: an ``OrderItem`` plus its lot number.

    The packaging, the quantity and the negotiated price are copied from the
    order line rather than read through it, for the same reason the receiver is
    snapshotted on ``DispatchEntry``: the challan states what physically went
    out, and a later edit to the order must not rewrite a challan already in the
    driver's hand.

    The lot number is the one field that exists nowhere else -- it identifies
    the production batch the bags came from, and it is captured when the
    dispatch is recorded.
    """

    dispatch_entry = models.ForeignKey(
        "aggregator.DispatchEntry",
        verbose_name="dispatch entry",
        on_delete=models.PROTECT,
        related_name="items",
    )
    product_packaging = models.ForeignKey(
        "aggregator.ProductPackaging",
        verbose_name="product packaging",
        on_delete=models.PROTECT,
        related_name="dispatch_entry_items",
    )
    negotiated_selling_price = models.DecimalField(
        "negotiated selling price per packaging",
        max_digits=12,
        decimal_places=2,
        help_text="The order line's whole-packaging price, copied at dispatch time.",
    )
    quantity = models.PositiveIntegerField("quantity")
    lot_number = models.CharField(
        "lot number",
        max_length=64,
        help_text="The production batch these bags came from.",
    )

    class Meta:
        verbose_name = "dispatch entry item"
        verbose_name_plural = "dispatch entry items"
        ordering = ["dispatch_entry", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["dispatch_entry", "product_packaging"],
                name="uniq_dispatchentryitem_entry_packaging",
            ),
            models.CheckConstraint(
                condition=models.Q(negotiated_selling_price__gte=0) & models.Q(quantity__gt=0),
                name="ck_dispatchentryitem_positive",
            ),
        ]

    def __str__(self):
        if self.product_packaging_id:
            return f"{self.quantity} × {self.product_packaging} (lot {self.lot_number})"
        return "dispatch entry item"

    @property
    def line_total(self):
        return self.negotiated_selling_price * self.quantity
