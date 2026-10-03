from django.db import models


class StockPoolKind(models.IntegerChoices):
    """Which pool a ``StockEventLine`` moves (``stock_event_line.pool_kind``)."""

    BAG = 1
    LOOSE = 2
    RAW = 3
    OTHER = 4


def _delta() -> models.DecimalField:
    return models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)


class StockEventLine(models.Model):
    """The signed change one ``StockEvent`` made to one pool.

    Exactly the pool reference matching ``pool_kind`` is set: ``BAG`` names a
    ``product_packaging``, ``LOOSE`` a ``packet_weight``, ``OTHER`` a
    ``material_type``, and ``RAW`` none (it is one pool per product). Delta
    columns a pool does not use stay NULL. Only deltas are stored -- ``available``
    and every other derived figure is recomputed when the report is built.
    """

    event = models.ForeignKey(
        "aggregator.StockEvent",
        verbose_name="event",
        on_delete=models.PROTECT,
        related_name="lines",
    )
    pool_kind = models.PositiveSmallIntegerField(
        "pool kind", choices=StockPoolKind.choices
    )
    product_packaging = models.ForeignKey(
        "aggregator.ProductPackaging",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    packet_weight = models.DecimalField(
        "packet weight", max_digits=8, decimal_places=3, null=True, blank=True
    )
    material_type = models.ForeignKey(
        "aggregator.OtherMaterialType",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    d_on_hand = _delta()
    d_reserved = _delta()
    d_consumed = _delta()
    d_incoming = _delta()
    d_packed = _delta()
    d_rejected = _delta()
    d_wasted = _delta()

    class Meta:
        verbose_name = "stock event line"
        verbose_name_plural = "stock event lines"
        ordering = ["event_id", "id"]
        indexes = [
            models.Index(fields=["event"], name="ix_stock_event_line_event"),
            models.Index(
                fields=["material_type", "event"],
                name="ix_stock_event_line_material",
                condition=models.Q(material_type__isnull=False),
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        pool_kind=StockPoolKind.BAG,
                        product_packaging__isnull=False,
                        packet_weight__isnull=True,
                        material_type__isnull=True,
                    )
                    | models.Q(
                        pool_kind=StockPoolKind.LOOSE,
                        product_packaging__isnull=True,
                        packet_weight__isnull=False,
                        material_type__isnull=True,
                    )
                    | models.Q(
                        pool_kind=StockPoolKind.RAW,
                        product_packaging__isnull=True,
                        packet_weight__isnull=True,
                        material_type__isnull=True,
                    )
                    | models.Q(
                        pool_kind=StockPoolKind.OTHER,
                        product_packaging__isnull=True,
                        packet_weight__isnull=True,
                        material_type__isnull=False,
                    )
                ),
                name="ck_stockeventline_pool_ref",
            ),
        ]

    def __str__(self):
        return f"{StockPoolKind(self.pool_kind).name} line of event {self.event_id}"
