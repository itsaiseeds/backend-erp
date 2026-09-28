from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class DispatchEntryItem(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A single line of a ``DispatchEntry``: an order line plus its lot number.

    Either a **bag** line, copied from an ``OrderItem`` (``product_packaging``
    set, ``quantity`` in bags, price per bag), or a **loose** line, copied from
    a ``CustomOrderItem`` (``product`` + ``packet_weight`` set, ``quantity`` in
    packets, price per packet). Exactly one of the two shapes
    (``ck_dispatchentryitem_one_kind``).

    The packaging and the negotiated price are copied from the order line
    rather than read through it, for the same reason the receiver is
    snapshotted on ``DispatchEntry``: the challan states what physically went
    out, and a later edit to the order must not rewrite a challan already in the
    driver's hand.

    ``quantity`` is **what actually shipped**, not the order line's quantity --
    the two may differ when a dispatch does not fully cover a line (fewer bags
    were on the floor than were ordered). ``InventoryOperations`` reads this
    figure as the truth for consumed bags, and treats the gap against the order
    line's quantity as still reserved (see ``reserved_bags``). Fixing that gap
    is a manual step -- edit the order's line down to what actually shipped, or
    revert the dispatch and re-record it -- there is no automatic follow-up
    shipment.

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
        null=True,
        blank=True,
        related_name="dispatch_entry_items",
        help_text="The bag, on an order's challan. Null on a loose line.",
    )
    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dispatch_entry_items",
        help_text="The product, on a custom order's loose line. Null on a bag line.",
    )
    packet_weight = models.DecimalField(
        "packet weight",
        max_digits=8,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Weight of one loose packet, in kg. Null on a bag line.",
    )
    negotiated_selling_price = models.DecimalField(
        "negotiated selling price per unit",
        max_digits=12,
        decimal_places=2,
        help_text=(
            "The order line's price per unit -- per bag or per loose packet -- "
            "copied at dispatch time."
        ),
    )
    quantity = models.PositiveIntegerField(
        "quantity", help_text="Bags on a bag line, packets on a loose line."
    )
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
            models.UniqueConstraint(
                fields=["dispatch_entry", "product", "packet_weight"],
                name="uniq_dispatchentryitem_entry_product_weight",
            ),
            models.CheckConstraint(
                condition=models.Q(negotiated_selling_price__gte=0) & models.Q(quantity__gt=0),
                name="ck_dispatchentryitem_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        product_packaging__isnull=False,
                        product__isnull=True,
                        packet_weight__isnull=True,
                    )
                    | models.Q(
                        product_packaging__isnull=True,
                        product__isnull=False,
                        packet_weight__isnull=False,
                    )
                ),
                name="ck_dispatchentryitem_one_kind",
            ),
        ]

    def __str__(self):
        if self.product_packaging_id:
            return f"{self.quantity} × {self.product_packaging} (lot {self.lot_number})"
        if self.product_id:
            return (
                f"{self.quantity} × {self.packet_weight}kg {self.product.name} "
                f"(lot {self.lot_number})"
            )
        return "dispatch entry item"

    @property
    def total_packets(self):
        """Packets on this line: bags x packets per bag, or the loose count itself."""
        if self.product_packaging_id:
            return self.quantity * self.product_packaging.packets
        return self.quantity

    @property
    def line_total(self):
        return self.negotiated_selling_price * self.quantity
