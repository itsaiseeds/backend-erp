from __future__ import annotations

from django.db import models

from common.models import indian_now


class StockEventType(models.IntegerChoices):
    """What kind of write moved a product's stock (``stock_event.event_type``).

    ``OPENING_BALANCE`` and ``CLOSING_BALANCE`` are deliberately absent: they
    are synthetic rows built in the report response and never stored.
    """

    LEDGER_START = 1
    INWARD_OPERATIONS = 2
    RAW_WASTED = 3
    PACKED = 4
    STOCK_ADJUSTED = 5
    STOCK_COUNTED = 6
    ORDER_CONFIRMED = 7
    ORDER_EDITED = 8
    ORDER_RELEASED = 9
    ORDER_DISPATCHED = 10
    DISPATCH_REVERTED = 11


class StockEventDetail(models.IntegerChoices):
    """The sub-reason of a ``StockEventType`` (``stock_event.detail``).

    Values are unique across event types, so a stored detail never needs its
    event type to be decoded. ``VALID_DETAILS`` lists which are legal per type.
    """

    NONE = 0
    SEED = 1

    RAW_LOT_IN_USE = 10
    RAW_LOT_REJECTED = 11
    RAW_LOT_BACK_TO_LAB = 12
    RAW_LOT_DELETED = 13
    OTHER_MATERIAL_RECEIVED = 14
    OTHER_MATERIAL_EDITED = 15
    OTHER_MATERIAL_DELETED = 16

    WASTE_RECORDED = 20
    WASTE_EDITED = 21
    WASTE_DELETED = 22

    BAG_COUNT = 30
    LOOSE_COUNT = 31
    COUNT_DELETED = 32
    CARRIED_FORWARD = 33

    ORDER_VERIFIED = 40
    CUSTOM_ORDER_CREATED = 41

    ORDER_LINES_CHANGED = 50
    CUSTOM_ORDER_LINES_CHANGED = 51

    UNVERIFIED = 60
    HELD = 61
    REJECTED = 62
    CUSTOM_ORDER_WITHDRAWN = 63

    FULL = 70
    PARTIAL = 71


VALID_DETAILS: dict[int, frozenset[int]] = {
    StockEventType.LEDGER_START: frozenset({StockEventDetail.SEED}),
    StockEventType.INWARD_OPERATIONS: frozenset(
        {
            StockEventDetail.RAW_LOT_IN_USE,
            StockEventDetail.RAW_LOT_REJECTED,
            StockEventDetail.RAW_LOT_BACK_TO_LAB,
            StockEventDetail.RAW_LOT_DELETED,
            StockEventDetail.OTHER_MATERIAL_RECEIVED,
            StockEventDetail.OTHER_MATERIAL_EDITED,
            StockEventDetail.OTHER_MATERIAL_DELETED,
        }
    ),
    StockEventType.RAW_WASTED: frozenset(
        {
            StockEventDetail.WASTE_RECORDED,
            StockEventDetail.WASTE_EDITED,
            StockEventDetail.WASTE_DELETED,
        }
    ),
    StockEventType.PACKED: frozenset(
        {StockEventDetail.BAG_COUNT, StockEventDetail.LOOSE_COUNT}
    ),
    StockEventType.STOCK_ADJUSTED: frozenset(
        {
            StockEventDetail.BAG_COUNT,
            StockEventDetail.LOOSE_COUNT,
            StockEventDetail.COUNT_DELETED,
        }
    ),
    StockEventType.STOCK_COUNTED: frozenset(
        {
            StockEventDetail.BAG_COUNT,
            StockEventDetail.LOOSE_COUNT,
            StockEventDetail.CARRIED_FORWARD,
        }
    ),
    StockEventType.ORDER_CONFIRMED: frozenset(
        {StockEventDetail.ORDER_VERIFIED, StockEventDetail.CUSTOM_ORDER_CREATED}
    ),
    StockEventType.ORDER_EDITED: frozenset(
        {
            StockEventDetail.ORDER_LINES_CHANGED,
            StockEventDetail.CUSTOM_ORDER_LINES_CHANGED,
        }
    ),
    StockEventType.ORDER_RELEASED: frozenset(
        {
            StockEventDetail.UNVERIFIED,
            StockEventDetail.HELD,
            StockEventDetail.REJECTED,
            StockEventDetail.CUSTOM_ORDER_WITHDRAWN,
        }
    ),
    StockEventType.ORDER_DISPATCHED: frozenset(
        {StockEventDetail.FULL, StockEventDetail.PARTIAL}
    ),
    StockEventType.DISPATCH_REVERTED: frozenset({StockEventDetail.NONE}),
}


def _source_fk(target: str) -> models.ForeignKey:
    """A nullable, unnamed-reverse FK to one of the event's possible sources."""
    return models.ForeignKey(
        target,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )


class StockEvent(models.Model):
    """One write's effect on one product's stock -- the header of the ledger.

    Append-only. The figures live in ``StockEventLine`` as signed deltas, one
    line per pool the write changed; running totals are rebuilt at read time.
    Nothing descriptive (client, lot no, party) is stored here: the source FKs
    are joined when the report is built. A write that touches several products
    writes one event per product.
    """

    event_type = models.PositiveSmallIntegerField(
        "event type", choices=StockEventType.choices
    )
    detail = models.PositiveSmallIntegerField(
        "detail", choices=StockEventDetail.choices
    )
    occurred_at = models.DateTimeField("occurred at", default=indian_now)
    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="stock_events",
    )
    actor = _source_fk("authentication.User")
    order = _source_fk("aggregator.Order")
    custom_order = _source_fk("aggregator.CustomOrder")
    inward_raw_material = _source_fk("aggregator.InwardRawMaterial")
    inward_other_material = _source_fk("aggregator.InwardOtherMaterial")
    raw_material_waste = _source_fk("aggregator.RawMaterialWaste")
    inventory_snapshot = _source_fk("aggregator.InventorySnapshot")
    loose_stock_snapshot = _source_fk("aggregator.LooseStockSnapshot")

    class Meta:
        verbose_name = "stock event"
        verbose_name_plural = "stock events"
        ordering = ["occurred_at", "id"]
        indexes = [
            models.Index(
                fields=["product", "occurred_at", "id"],
                name="ix_stock_event_product_time",
            ),
        ]

    def __str__(self):
        return (
            f"{self.occurred_at:%Y-%m-%d %H:%M} "
            f"{StockEventType(self.event_type).name}/"
            f"{StockEventDetail(self.detail).name} product={self.product_id}"
        )
