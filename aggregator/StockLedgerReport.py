"""The product stock ledger report: running figures rebuilt from stored deltas.

``product_ledger_rows`` replays a product's events oldest first. A row lists
**every** pool of the product (the full state after the event) plus what the
event changed, so ``row k`` plus ``change(k+1)`` equals ``row k+1``.
``OPENING_BALANCE`` and ``CLOSING_BALANCE`` are synthetic rows built here and
never stored.

Which events a product's report lists (PRD section 3.6):

* every event stored against the product;
* ``INWARD_OPERATIONS`` events of **other** products that touch one of this
  product's packing-material types (a lot booked against another product's
  recipe still changes the shared pool).

Other products' packing of a shared material is not a row, but it moves the
running ``used_by_other_products``, so every row still reconciles:
``incoming - packed - used_by_other_products = available``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from . import InventoryOperations
from .models import (
    OtherMaterialType,
    Product,
    ProductPackaging,
    StockEvent,
    StockEventDetail,
    StockEventLine,
    StockEventType,
    StockPoolKind,
)
from .StockLedgerOperations import (
    LINE_FIELDS,
    ZERO,
    _weight,
    product_material_type_ids,
)

BAG = StockPoolKind.BAG
LOOSE = StockPoolKind.LOOSE
RAW = StockPoolKind.RAW
OTHER = StockPoolKind.OTHER

QUANT = Decimal("0.001")


class LedgerNotStarted(Exception):
    """The ledger has no ``LEDGER_START`` event: ``seed_stock_ledger`` has not run."""


class LedgerRangeError(Exception):
    """The requested window starts before the ledger does."""


def ledger_start() -> datetime | None:
    """When the ledger went live: its earliest ``LEDGER_START`` event."""
    return (
        StockEvent.objects.filter(event_type=StockEventType.LEDGER_START)
        .order_by("occurred_at")
        .values_list("occurred_at", flat=True)
        .first()
    )


def day_start(day: date) -> datetime:
    """Midnight at the start of ``day`` in the project's timezone (IST)."""
    return datetime.combine(day, time.min, tzinfo=timezone.get_current_timezone())


def _fmt(value: Decimal) -> str:
    return str(Decimal(value).quantize(QUANT))


@dataclass
class _State:
    """Running figures of one product, advanced event by event."""

    bags: dict[int, dict[str, Decimal]] = field(default_factory=dict)
    loose: dict[Decimal, dict[str, Decimal]] = field(default_factory=dict)
    raw: dict[str, Decimal] = field(
        default_factory=lambda: dict.fromkeys(LINE_FIELDS[RAW], ZERO)
    )
    other: dict[int, dict[str, Decimal]] = field(default_factory=dict)

    def apply(self, line: StockEventLine, *, own: bool) -> None:
        """Add one line. ``own`` is False for another product's event, of which
        only the packing-material pool (shared) is relevant."""
        kind = line.pool_kind
        if kind == OTHER:
            figures = self.other.setdefault(
                line.material_type_id or 0,
                {"incoming": ZERO, "packed": ZERO, "used_by_others": ZERO},
            )
            figures["incoming"] += line.d_incoming or ZERO
            figures["packed" if own else "used_by_others"] += line.d_packed or ZERO
            return
        if not own:
            return
        if kind == BAG:
            figures = self.bags.setdefault(
                line.product_packaging_id or 0, dict.fromkeys(LINE_FIELDS[BAG], ZERO)
            )
        elif kind == LOOSE:
            figures = self.loose.setdefault(
                _weight(line.packet_weight or ZERO), dict.fromkeys(LINE_FIELDS[LOOSE], ZERO)
            )
        else:
            figures = self.raw
        for name in LINE_FIELDS[kind]:
            figures[name] += getattr(line, f"d_{name}") or ZERO


def _available(figures: dict[str, Decimal], kind: int) -> Decimal:
    if kind in (BAG, LOOSE):
        return figures["on_hand"] - figures["reserved"] - figures["consumed"]
    if kind == RAW:
        return figures["incoming"] - figures["packed"] - figures["wasted"]
    return figures["incoming"] - figures["packed"] - figures["used_by_others"]


def _count_block(now: dict[str, Decimal], delta: dict[str, Decimal]) -> dict[str, object]:
    """A bag or loose pool's figures (whole numbers) and the event's change."""
    return {
        "on_hand": int(now["on_hand"]),
        "reserved": int(now["reserved"]),
        "consumed": int(now["consumed"]),
        "available": int(_available(now, BAG)),
        "change": {
            "on_hand": int(delta["on_hand"]),
            "reserved": int(delta["reserved"]),
            "consumed": int(delta["consumed"]),
            "available": int(_available(delta, BAG)),
        },
    }


def _pool_payloads(
    state: _State,
    change: _State,
    packagings: list[ProductPackaging],
    weights: list[Decimal],
    materials: list[OtherMaterialType],
) -> dict[str, object]:
    zero_count = dict.fromkeys(LINE_FIELDS[BAG], ZERO)
    zero_other = {"incoming": ZERO, "packed": ZERO, "used_by_others": ZERO}

    bag_pools = [
        {
            "packaging": {
                "public_id": packaging.public_id,
                "packet_weight": _fmt(packaging.packet_weight),
                "packets": packaging.packets,
            },
            **_count_block(
                state.bags.get(packaging.pk, zero_count),
                change.bags.get(packaging.pk, zero_count),
            ),
        }
        for packaging in packagings
    ]
    packet_pools = [
        {
            "packet_weight": _fmt(weight),
            **_count_block(
                state.loose.get(weight, zero_count), change.loose.get(weight, zero_count)
            ),
        }
        for weight in weights
    ]
    raw_material = {
        **{name: _fmt(state.raw[name]) for name in LINE_FIELDS[RAW]},
        "available": _fmt(_available(state.raw, RAW)),
        "change": {
            **{name: _fmt(change.raw[name]) for name in LINE_FIELDS[RAW]},
            "available": _fmt(_available(change.raw, RAW)),
        },
    }
    other_materials = []
    for material in materials:
        now = state.other.get(material.pk, zero_other)
        delta = change.other.get(material.pk, zero_other)
        other_materials.append(
            {
                "material_type": {
                    "id": material.pk,
                    "name": material.name,
                    "unit_type": material.unit_type,
                },
                "incoming": _fmt(now["incoming"]),
                "packed": _fmt(now["packed"]),
                "used_by_other_products": _fmt(now["used_by_others"]),
                "available": _fmt(_available(now, OTHER)),
                "change": {
                    "incoming": _fmt(delta["incoming"]),
                    "packed": _fmt(delta["packed"]),
                    "used_by_other_products": _fmt(delta["used_by_others"]),
                    "available": _fmt(_available(delta, OTHER)),
                },
            }
        )
    return {
        "bag_pools": bag_pools,
        "packet_pools": packet_pools,
        "raw_material": raw_material,
        "other_materials": other_materials,
    }


def _source_payload(event: StockEvent, product: Product) -> dict[str, object] | None:
    """The row behind an event, joined at read time -- nothing is stored."""
    if event.order_id:
        order = event.order
        return {
            "kind": "order",
            "public_id": order.public_id,
            "label": order.client.company_name,
        }
    if event.custom_order_id:
        order = event.custom_order
        return {
            "kind": "custom_order",
            "public_id": order.public_id,
            "label": order.client.company_name,
        }
    if event.inward_raw_material_id:
        lot = event.inward_raw_material
        return {"kind": "inward_raw_material", "public_id": lot.public_id, "label": lot.lot_no}
    if event.inward_other_material_id:
        lot = event.inward_other_material
        label = lot.recipe.material_type.name
        if event.product_id != product.pk:
            label = f"{label} ({event.product.name})"
        return {"kind": "inward_other_material", "public_id": lot.public_id, "label": label}
    if event.raw_material_waste_id:
        waste = event.raw_material_waste
        return {"kind": "raw_material_waste", "public_id": waste.public_id, "label": waste.reason}
    if event.inventory_snapshot_id:
        snapshot = event.inventory_snapshot
        return {
            "kind": "bag_count",
            "public_id": snapshot.public_id,
            "label": snapshot.snapshot_date.isoformat(),
        }
    if event.loose_stock_snapshot_id:
        snapshot = event.loose_stock_snapshot
        return {
            "kind": "loose_count",
            "public_id": snapshot.public_id,
            "label": snapshot.snapshot_date.isoformat(),
        }
    return None


def _actor_payload(event: StockEvent) -> dict[str, object] | None:
    if event.actor_id is None:
        return None
    return {"id": event.actor_id, "name": event.actor.display_name}


def _window_events(
    product: Product, material_ids: list[int], window_end: datetime
) -> list[StockEvent]:
    """The product's events plus other products' events on its materials."""
    own = StockEvent.objects.filter(product=product, occurred_at__lt=window_end)
    others = (
        StockEvent.objects.exclude(product=product)
        .filter(occurred_at__lt=window_end, lines__material_type_id__in=material_ids)
        .distinct()
    )
    return list(
        StockEvent.objects.filter(
            pk__in=[*own.values_list("pk", flat=True), *others.values_list("pk", flat=True)]
        )
        .select_related(
            "product",
            "actor",
            "order__client",
            "custom_order__client",
            "inward_raw_material",
            "inward_other_material__recipe__material_type",
            "raw_material_waste",
            "inventory_snapshot",
            "loose_stock_snapshot",
        )
        .prefetch_related("lines")
        .order_by("occurred_at", "id")
    )


def product_ledger_rows(
    product: Product, start_date: date, end_date: date
) -> list[dict[str, object]]:
    """Every report row for ``product`` over the inclusive IST window.

    ``OPENING_BALANCE`` first, ``CLOSING_BALANCE`` last, the window's events in
    between. Running totals cover the whole range, so a caller may slice the
    list into pages freely. Raises :class:`LedgerNotStarted` before the ledger
    is seeded and :class:`LedgerRangeError` for a window starting before it.
    """
    go_live = ledger_start()
    if go_live is None:
        raise LedgerNotStarted
    first_day = timezone.localtime(go_live).date()
    if start_date < first_day:
        raise LedgerRangeError(f"Stock ledger starts on {first_day.isoformat()}")
    window_start = day_start(start_date)
    window_end = day_start(end_date + timedelta(days=1))

    material_ids = product_material_type_ids(product)
    events = _window_events(product, material_ids, window_end)

    packagings = list(
        ProductPackaging.all_objects.filter(product=product).order_by("packet_weight", "pk")
    )
    weights = {
        _weight(weight) for weight in InventoryOperations.product_loose_weights(product)
    }
    for event in events:
        if event.product_id != product.pk:
            continue
        weights.update(
            _weight(line.packet_weight)
            for line in event.lines.all()
            if line.pool_kind == LOOSE and line.packet_weight is not None
        )
    ordered_weights = sorted(weights)
    materials = list(
        OtherMaterialType.all_objects.filter(pk__in=material_ids).order_by("name", "pk")
    )

    state = _State()

    def row(
        name: str,
        detail: str | None,
        occurred_at: datetime,
        change: _State,
        event: StockEvent | None = None,
    ) -> dict[str, object]:
        return {
            "event": name,
            "detail": detail,
            "occurred_at": timezone.localtime(occurred_at).isoformat(),
            "source": _source_payload(event, product) if event else None,
            "actor": _actor_payload(event) if event else None,
            **_pool_payloads(state, change, packagings, ordered_weights, materials),
        }

    rows: list[dict[str, object]] = []
    opening: dict[str, object] | None = None
    for event in events:
        in_window = event.occurred_at >= window_start
        if in_window and opening is None:
            opening = row("OPENING_BALANCE", None, window_start, _State())
        is_own = event.product_id == product.pk
        change = _State()
        for line in event.lines.all():
            if not is_own and line.material_type_id not in material_ids:
                continue
            state.apply(line, own=is_own)
            change.apply(line, own=is_own)
        if not in_window:
            continue
        if not is_own and event.event_type != StockEventType.INWARD_OPERATIONS:
            continue  # another product's packing only moves used_by_other_products
        detail = StockEventDetail(event.detail)
        rows.append(
            row(
                StockEventType(event.event_type).name,
                None if detail == StockEventDetail.NONE else detail.name,
                event.occurred_at,
                change,
                event,
            )
        )
    if opening is None:
        opening = row("OPENING_BALANCE", None, window_start, _State())
    closing = row("CLOSING_BALANCE", None, window_end, _State())
    return [opening, *rows, closing]
