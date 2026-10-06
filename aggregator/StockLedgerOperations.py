"""Product stock ledger: recording stock events as the diff of live figures.

The ledger is an append-only list of signed deltas (``StockEvent`` headers with
``StockEventLine`` children). It is never computed from first principles: every
write that can move stock runs inside :func:`recording`, which reads the live
figures of the products it touches **with the same functions the stock screens
use** (``InventoryOperations``), lets the write run, reads them again and stores
only the difference. The ledger therefore equals the live screens by
construction, and a rolled-back write rolls its ledger rows back with it.

Two ideas keep the stored data small:

* only deltas are stored (unused delta columns stay NULL), never derived
  figures, text or JSON;
* a write that moves no figure writes no event.

Figures per pool (see ``docs/prd/product-stock-ledger.md`` section 3.2):

* ``BAG`` (per ``ProductPackaging``) and ``LOOSE`` (per packet weight):
  ``on_hand``, ``reserved``, ``consumed``;
* ``RAW`` (one per product): ``incoming``, ``packed``, ``rejected``, ``wasted``;
* ``OTHER`` (per packing-material type): ``incoming`` (pool-wide) and ``packed``
  (this product's usage). The pool-wide ``incoming`` delta is written once per
  write, on the first product's event that carries it, so summing a material
  type's lines across products never double counts it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models, transaction

from common.models import indian_now

from . import InventoryOperations
from .models import (
    CustomOrder,
    CustomOrderItem,
    DispatchEntryItem,
    InventorySnapshot,
    InwardOtherMaterial,
    InwardRawMaterial,
    LooseStockSnapshot,
    Order,
    OrderItem,
    OtherMaterialRecipe,
    Product,
    ProductPackaging,
    RawMaterialWaste,
    ReturnOrder,
    StatusIds,
    StockEvent,
    StockEventDetail,
    StockEventLine,
    StockEventType,
    StockPoolKind,
)

if TYPE_CHECKING:
    from authentication.models import User

ZERO = Decimal("0")
WEIGHT_QUANT = Decimal("0.001")

BAG = StockPoolKind.BAG
LOOSE = StockPoolKind.LOOSE
RAW = StockPoolKind.RAW
OTHER = StockPoolKind.OTHER

# The figures stored as deltas, per pool kind. ``packed_packets`` is also read
# for bag and loose pools (it classifies a count write) but is never stored.
LINE_FIELDS: dict[int, tuple[str, ...]] = {
    BAG: ("on_hand", "reserved", "consumed"),
    LOOSE: ("on_hand", "reserved", "consumed"),
    RAW: ("incoming", "packed", "rejected", "wasted"),
    OTHER: ("incoming", "packed"),
}

# A pool is addressed by (kind, ref): the packaging pk for BAG, the packet
# weight for LOOSE, 0 for RAW and the material-type id for OTHER.
PoolKey = tuple[int, int | Decimal]
Figures = dict[str, Decimal]
Position = dict[PoolKey, Figures]

# Source model -> the ``StockEvent`` FK that records it.
_SOURCE_FIELDS: dict[type[models.Model], str] = {
    Order: "order",
    CustomOrder: "custom_order",
    InwardRawMaterial: "inward_raw_material",
    InwardOtherMaterial: "inward_other_material",
    RawMaterialWaste: "raw_material_waste",
    InventorySnapshot: "inventory_snapshot",
    LooseStockSnapshot: "loose_stock_snapshot",
    ReturnOrder: "return_order",
}


# -- Reading the live position -------------------------------------------------


def _weight(value: Decimal) -> Decimal:
    return Decimal(value).quantize(WEIGHT_QUANT)


def product_material_type_ids(product: Product) -> list[int]:
    """Packing-material types ``product``'s recipes use (live or deleted)."""
    return sorted(
        set(
            OtherMaterialRecipe.all_objects.filter(product=product).values_list(
                "material_type_id", flat=True
            )
        )
    )


def _row_date(row: InventorySnapshot | LooseStockSnapshot | None) -> Decimal:
    """The date of the count row a pool reads from, as an ordinal (0 = no row).

    Never stored: it lets :func:`_sync_recipe_layers` tell a write that opened
    a newer row from a deletion that fell back to an older one.
    """
    return Decimal(row.snapshot_date.toordinal()) if row else ZERO


def read_position(
    product: Product,
    *,
    bag_date: date | None,
    loose_date: date | None,
) -> Position:
    """The live figures of every pool of ``product``.

    Built from the same functions the stock screens call, so the diff of two
    positions is exactly the change those screens would show.
    """
    from . import InwardOperations

    position: Position = {}
    packed_by_weight: dict[Decimal, int] = {}
    packaging_weights: set[Decimal] = set()

    for packaging in ProductPackaging.objects.filter(product=product).order_by("pk"):
        line = InventoryOperations.snapshot_line(packaging, bag_date)
        on_hand = line.bags if line else 0
        packed_bags = on_hand + InventoryOperations._bags_dispatched_before(
            packaging, bag_date
        )
        packed_packets = packed_bags * packaging.packets
        weight = _weight(packaging.packet_weight)
        packaging_weights.add(weight)
        packed_by_weight[weight] = packed_by_weight.get(weight, 0) + packed_packets
        position[(BAG, packaging.pk)] = {
            "on_hand": Decimal(on_hand),
            "reserved": Decimal(InventoryOperations.reserved_bags(packaging)),
            "consumed": Decimal(InventoryOperations.consumed_bags(packaging, bag_date)),
            "packed_packets": Decimal(packed_packets),
            "row_date": _row_date(line),
        }

    loose_weights = {
        _weight(weight)
        for weight in InventoryOperations.product_loose_weights(product)
    } | {
        _weight(weight)
        for weight in LooseStockSnapshot.objects.filter(product=product).values_list(
            "packet_weight", flat=True
        )
    }
    for weight in sorted(loose_weights):
        loose_row = InventoryOperations.loose_line(product, weight, loose_date)
        on_hand = loose_row.packets if loose_row else 0
        packed = on_hand + InventoryOperations._loose_dispatched_before(
            product, weight, loose_date
        )
        if weight in packaging_weights:
            packed_by_weight[weight] = packed_by_weight.get(weight, 0) + packed
        position[(LOOSE, weight)] = {
            "on_hand": Decimal(on_hand),
            "reserved": Decimal(InventoryOperations.reserved_loose_packets(product, weight)),
            "consumed": Decimal(
                InventoryOperations.consumed_loose_packets(product, weight, loose_date)
            ),
            "packed_packets": Decimal(packed),
            "row_date": _row_date(loose_row),
        }

    packed_kg = sum(
        (Decimal(packets) * weight for weight, packets in packed_by_weight.items()),
        ZERO,
    )
    rejected = InwardOperations._dated_raw_kg_by_product(
        StatusIds.RAW_MATERIAL_REJECTED.value,
        InventoryOperations.today(),
        [product.public_id],
    ).get(product.pk, {})
    position[(RAW, 0)] = {
        "incoming": InventoryOperations.raw_inward_kg(product),
        "packed": packed_kg,
        "rejected": rejected.get("kg", ZERO),
        "wasted": InventoryOperations.raw_wasted_kg(product),
    }

    material_type_ids = product_material_type_ids(product)
    if material_type_ids:
        incoming = InventoryOperations.other_material_inward(material_type_ids)
        used = other_material_used_by_product(product, material_type_ids)
        for material_type_id in material_type_ids:
            position[(OTHER, material_type_id)] = {
                "incoming": incoming.get(material_type_id, ZERO),
                "packed": used.get(material_type_id, ZERO),
            }
    return position


def other_material_used_by_product(
    product: Product, material_type_ids: Iterable[int]
) -> dict[int, Decimal]:
    """Units of each material type spent by ``product``'s own packed packets."""
    return InventoryOperations.other_material_used(material_type_ids, product=product)


def read_positions(product_ids: Iterable[int]) -> dict[int, Position]:
    """``{product_id: position}`` for every product in ``product_ids``."""
    bag_date = InventoryOperations.latest_snapshot_date()
    loose_date = InventoryOperations.latest_loose_snapshot_date()
    products = Product.all_objects.filter(pk__in=list(product_ids))
    return {
        product.pk: read_position(product, bag_date=bag_date, loose_date=loose_date)
        for product in products
    }


# -- Diffing -------------------------------------------------------------------


def diff_positions(before: Position, after: Position) -> dict[PoolKey, Figures]:
    """Per pool, the stored fields that moved, plus ``packed_packets``.

    Pools missing on one side count as zero there. A pool whose stored fields
    did not move is omitted, even if ``packed_packets`` did.
    """
    changes: dict[PoolKey, Figures] = {}
    for key in before.keys() | after.keys():
        kind = key[0]
        old = before.get(key, {})
        new = after.get(key, {})
        delta = {
            name: new.get(name, ZERO) - old.get(name, ZERO)
            for name in LINE_FIELDS[kind]
        }
        if not any(delta.values()):
            continue
        if "packed_packets" in new or "packed_packets" in old:
            delta["packed_packets"] = new.get("packed_packets", ZERO) - old.get(
                "packed_packets", ZERO
            )
        changes[key] = delta
    return changes


# -- Recording -----------------------------------------------------------------


@dataclass
class Recording:
    """The handle :func:`recording` yields.

    ``source`` (and per-product ``sources``) name the row behind the event and
    may be set inside the block, once the write has created it. ``event_type``
    and ``detail`` may be refined the same way (a dispatch only knows whether
    it was full or partial after it ran).
    """

    event_type: StockEventType | None
    detail: StockEventDetail
    source: models.Model | None = None
    sources: dict[int, models.Model] = field(default_factory=dict)
    actor: User | None = None
    # Pools a count write carried forward rather than counted (PRD section 3.5).
    # Keyed by product too: two products can share a packet weight.
    carried: set[tuple[int, PoolKey]] = field(default_factory=set)
    events: list[StockEvent] = field(default_factory=list)
    # Guards that need the packing-material figures *after* the write: material
    # usage is read from the recipe layers, which are only brought up to date
    # once the block ends, so a check inside the block cannot see the new
    # packets. These run right after that sync; raising rolls the write back.
    after_sync_checks: list[Callable[[], None]] = field(default_factory=list)


def _lock_products(product_ids: Iterable[int]) -> None:
    """Take the stock locks in the order every writer takes them.

    Raw pools, then bag pools, then loose pools, then materials. The write
    inside re-takes each as a no-op, so locking here costs nothing and means
    the "before" read can never be stale.
    """
    product_ids = sorted(set(product_ids))
    if not product_ids:
        return
    InventoryOperations.lock_raw_pools(product_ids)
    InventoryOperations.lock_bag_pools(
        ProductPackaging.all_objects.filter(product_id__in=product_ids)
    )
    InventoryOperations.lock_loose_pools(product_ids)
    InventoryOperations._lock_materials(product_ids)


def products_with_pools() -> set[int]:
    """Every product that has a packaging or a loose count row."""
    return set(ProductPackaging.objects.values_list("product_id", flat=True)) | set(
        LooseStockSnapshot.objects.values_list("product_id", flat=True)
    )


@contextmanager
def recording(
    event_type: StockEventType | None,
    detail: StockEventDetail,
    product_ids: Iterable[int],
    *,
    source: models.Model | None = None,
    actor: User | None = None,
    new_bag_date: date | None = None,
    new_loose_date: date | None = None,
) -> Iterator[Recording]:
    """Run a stock write and record what it moved.

    Use it around the write itself::

        with recording(StockEventType.RAW_WASTED, StockEventDetail.WASTE_RECORDED,
                       [product.id], actor=actor) as rec:
            waste = RawMaterialWaste.objects.create(...)
            rec.source = waste

    ``event_type=None`` means a **count write**: each product's changed pools
    are classified by how many packets were packed (PACKED / STOCK_ADJUSTED /
    STOCK_COUNTED, PRD section 3.3).

    ``new_bag_date`` / ``new_loose_date`` name the date a count write is about
    to record. A date past the latest count moves every product's reads, so the
    tracked products widen to every product with a pool.

    Opens its own ``transaction.atomic``: a write that raises rolls the ledger
    rows back with it, and nothing is recorded.
    """
    tracked = set(product_ids)
    with transaction.atomic():
        latest_bag = InventoryOperations.latest_snapshot_date()
        latest_loose = InventoryOperations.latest_loose_snapshot_date()
        if (new_bag_date is not None and (latest_bag is None or new_bag_date > latest_bag)) or (
            new_loose_date is not None
            and (latest_loose is None or new_loose_date > latest_loose)
        ):
            tracked |= products_with_pools()
        _lock_products(tracked)
        before = read_positions(tracked)
        handle = Recording(event_type, detail, source, actor=actor)
        yield handle
        after = read_positions(tracked)
        if _sync_recipe_layers(tracked, before, after):
            # Packing-material usage is read from the layers, so re-read.
            after = read_positions(tracked)
        for check in handle.after_sync_checks:
            check()
        _write_events(handle, tracked, before, after)


def _pool_row(
    product_id: int, key: PoolKey
) -> InventorySnapshot | LooseStockSnapshot | None:
    """The latest count row of a bag or loose pool, if it has one."""
    kind, ref = key
    if kind == BAG:
        latest = InventoryOperations.latest_snapshot_date()
        if latest is None:
            return None
        return InventorySnapshot.objects.filter(
            product_packaging_id=int(ref), snapshot_date=latest
        ).first()
    latest = InventoryOperations.latest_loose_snapshot_date()
    if latest is None:
        return None
    return LooseStockSnapshot.objects.filter(
        product_id=product_id, packet_weight=Decimal(ref), snapshot_date=latest
    ).first()


def _sync_recipe_layers(
    tracked: Iterable[int],
    before: dict[int, Position],
    after: dict[int, Position],
) -> bool:
    """Keep every pool's recipe layers in step with its packed packets.

    A write is the only moment a pool's packed packets change, and this is the
    one place both sides of the change are known: packing (delta > 0) layers
    the new packets at the live recipes, unpacking (delta < 0) removes them
    newest-first, and the sum of layers is finally clamped to the packed
    figure. Returns whether any pool changed.
    """
    changed = False
    for product_id in tracked:
        old = before.get(product_id, {})
        new = after.get(product_id, {})
        for key in old.keys() | new.keys():
            if key[0] not in (BAG, LOOSE):
                continue
            packed_before = int(old.get(key, {}).get("packed_packets", ZERO))
            packed_after = int(new.get(key, {}).get("packed_packets", ZERO))
            row = _pool_row(product_id, key)
            if row is None:
                continue
            delta = packed_after - packed_before
            # A deletion can fall back to an older row, whose layers already
            # describe what it packed: only clamp those, never re-apply a delta.
            row_date_before = old.get(key, {}).get("row_date", ZERO)
            row_date_after = new.get(key, {}).get("row_date", ZERO)
            if row_date_before and row_date_after < row_date_before:
                delta = 0
            if delta > 0:
                weight = (
                    row.product_packaging.packet_weight
                    if isinstance(row, InventorySnapshot)
                    else row.packet_weight
                )
                InventoryOperations.add_packed_packets(row, product_id, weight, delta)
            elif delta < 0:
                InventoryOperations.remove_packed_packets(row, -delta)
            trimmed = InventoryOperations.clamp_recipe_layers(row, packed_after)
            changed = changed or delta != 0 or trimmed
    return changed


def _group_changes(
    changes: dict[PoolKey, Figures],
    event_type: StockEventType | None,
    detail: StockEventDetail,
    carried: set[PoolKey],
) -> list[tuple[StockEventType, StockEventDetail, list[PoolKey]]]:
    """Split one product's changed pools into ``(event_type, detail, pools)``.

    A fixed ``event_type`` keeps them together. A count write (``None``)
    splits by packed-packet change, with carried-forward pools in events of
    their own; raw and packing-material lines ride on the first event, since
    they are the consequence of the packing change as a whole.
    """
    keys = sorted(changes, key=lambda key: (key[0], str(key[1])))
    if event_type is not None:
        return [(event_type, detail, keys)]

    pool_keys = [key for key in keys if key[0] in (BAG, LOOSE)]
    rest = [key for key in keys if key[0] not in (BAG, LOOSE)]
    buckets: dict[tuple[StockEventType, bool], list[PoolKey]] = {}
    for key in pool_keys:
        packed = changes[key].get("packed_packets", ZERO)
        if packed > 0:
            bucket = StockEventType.PACKED
        elif packed < 0:
            bucket = StockEventType.STOCK_ADJUSTED
        else:
            bucket = StockEventType.STOCK_COUNTED
        buckets.setdefault((bucket, key in carried), []).append(key)

    order = [
        (bucket, is_carried)
        for is_carried in (False, True)
        for bucket in (
            StockEventType.PACKED,
            StockEventType.STOCK_ADJUSTED,
            StockEventType.STOCK_COUNTED,
        )
        if (bucket, is_carried) in buckets
    ]
    if not order:
        raw_packed = changes.get((RAW, 0), {}).get("packed", ZERO)
        fallback = (
            StockEventType.PACKED
            if raw_packed > 0
            else StockEventType.STOCK_ADJUSTED
            if raw_packed < 0
            else StockEventType.STOCK_COUNTED
        )
        return [(fallback, detail, rest)]
    groups = [
        (
            bucket,
            StockEventDetail.CARRIED_FORWARD if is_carried else detail,
            buckets[(bucket, is_carried)],
        )
        for bucket, is_carried in order
    ]
    groups[0] = (groups[0][0], groups[0][1], groups[0][2] + rest)
    return groups


def _source_kwargs(model: models.Model | None) -> dict[str, models.Model]:
    if model is None:
        return {}
    for model_class, field_name in _SOURCE_FIELDS.items():
        if isinstance(model, model_class):
            return {field_name: model}
    return {}


def _write_events(
    handle: Recording,
    tracked: Iterable[int],
    before: dict[int, Position],
    after: dict[int, Position],
) -> None:
    occurred_at = indian_now()
    incoming_written: set[int] = set()
    for product_id in sorted(tracked):
        changes = diff_positions(before.get(product_id, {}), after.get(product_id, {}))
        # A material type's ``incoming`` is pool-wide: record it once per write.
        for key, delta in list(changes.items()):
            if key[0] != OTHER or not delta.get("incoming"):
                continue
            if key[1] in incoming_written:
                delta["incoming"] = ZERO
                if not any(delta[name] for name in LINE_FIELDS[OTHER]):
                    del changes[key]
            else:
                incoming_written.add(int(key[1]))
        if not changes:
            continue
        groups = _group_changes(
            changes,
            handle.event_type,
            handle.detail,
            {key for owner, key in handle.carried if owner == product_id},
        )
        for event_type, detail, keys in groups:
            if not keys:
                continue
            row_source = handle.sources.get(product_id, handle.source)
            event = StockEvent.objects.create(
                event_type=event_type,
                detail=detail,
                occurred_at=occurred_at,
                product_id=product_id,
                actor=handle.actor,
                **_source_kwargs(row_source),
            )
            StockEventLine.objects.bulk_create(
                _line(event, key, changes[key]) for key in keys
            )
            handle.events.append(event)


def _line(event: StockEvent, key: PoolKey, delta: Figures) -> StockEventLine:
    kind, ref = key
    line = StockEventLine(event=event, pool_kind=kind)
    if kind == BAG:
        line.product_packaging_id = int(ref)
    elif kind == LOOSE:
        line.packet_weight = Decimal(ref)
    elif kind == OTHER:
        line.material_type_id = int(ref)
    for name in LINE_FIELDS[kind]:
        value = delta.get(name, ZERO)
        setattr(line, f"d_{name}", value if value else None)
    return line


# -- Helpers for the order flows ----------------------------------------------


def order_product_ids(order: Order, extra: Iterable[int] = ()) -> set[int]:
    """Products on ``order``'s lines, removed lines included, plus ``extra``."""
    return set(extra) | set(
        OrderItem.all_objects.filter(order=order).values_list(
            "product_packaging__product_id", flat=True
        )
    )


def custom_order_product_ids(
    order: CustomOrder, extra: Iterable[int] = ()
) -> set[int]:
    """Products on ``order``'s lines, removed lines included, plus ``extra``."""
    return set(extra) | set(
        CustomOrderItem.all_objects.filter(custom_order=order).values_list(
            "product_id", flat=True
        )
    )


def dispatch_detail(order: Order) -> StockEventDetail:
    """``PARTIAL`` when any line shipped fewer bags than it ordered, else ``FULL``."""
    shipped: dict[int, int] = {}
    for packaging_id, quantity in DispatchEntryItem.objects.filter(
        dispatch_entry__order=order
    ).values_list("product_packaging_id", "quantity"):
        shipped[packaging_id] = shipped.get(packaging_id, 0) + quantity
    for packaging_id, quantity in OrderItem.objects.filter(order=order).values_list(
        "product_packaging_id", "quantity"
    ):
        if shipped.get(packaging_id, 0) < quantity:
            return StockEventDetail.PARTIAL
    return StockEventDetail.FULL


# -- Go-live seed and the integrity check --------------------------------------


def _zero_delta_event(product_id: int, occurred_at: datetime) -> StockEvent:
    return StockEvent.objects.create(
        event_type=StockEventType.LEDGER_START,
        detail=StockEventDetail.SEED,
        occurred_at=occurred_at,
        product_id=product_id,
    )


@transaction.atomic
def seed_ledger() -> int:
    """Write the go-live ``LEDGER_START`` events. Returns how many were written.

    One event per product, with a line per pool whose live figure is non-zero
    (deltas from zero up to the live position). The recipe layers of every
    existing latest count row are seeded first, at the current recipes, since
    packing-material usage is read from them. No live figure moves: the seed
    only records where each one already stands. Refuses to run twice.
    """
    if StockEvent.objects.filter(event_type=StockEventType.LEDGER_START).exists():
        raise ValueError("The stock ledger has already been seeded.")
    if StockEvent.objects.exists():
        # The seed records the whole live position, so seeding on top of
        # events that already recorded part of it would count that part twice.
        raise ValueError("The stock ledger already has events; seed it before it records any.")
    InventoryOperations.seed_recipe_layers()
    occurred_at = indian_now()
    positions = read_positions(Product.all_objects.values_list("pk", flat=True))
    incoming_written: set[int] = set()
    count = 0
    for product_id in sorted(positions):
        changes = diff_positions({}, positions[product_id])
        for key, delta in list(changes.items()):
            if key[0] != OTHER or not delta.get("incoming"):
                continue
            if key[1] in incoming_written:
                delta["incoming"] = ZERO
                if not any(delta[name] for name in LINE_FIELDS[OTHER]):
                    del changes[key]
            else:
                incoming_written.add(int(key[1]))
        event = _zero_delta_event(product_id, occurred_at)
        StockEventLine.objects.bulk_create(
            _line(event, key, changes[key]) for key in sorted(changes, key=str)
        )
        count += 1
    return count


def ledger_positions(product_ids: Iterable[int]) -> dict[int, Position]:
    """Each product's figures as the ledger says they are: the sum of its deltas.

    A packing-material type's ``incoming`` is pool-wide, so it is summed over
    every product's lines of that type.
    """
    product_ids = list(product_ids)
    sums = {name: models.Sum(f"d_{name}") for name in (
        "on_hand", "reserved", "consumed", "incoming", "packed", "rejected", "wasted"
    )}
    rows = (
        StockEventLine.objects.filter(event__product_id__in=product_ids)
        .values(
            "event__product_id",
            "pool_kind",
            "product_packaging_id",
            "packet_weight",
            "material_type_id",
        )
        .annotate(**sums)
    )
    positions: dict[int, Position] = {pid: {} for pid in product_ids}
    for row in rows:
        kind = row["pool_kind"]
        ref: int | Decimal
        if kind == BAG:
            ref = row["product_packaging_id"]
        elif kind == LOOSE:
            ref = _weight(row["packet_weight"] or ZERO)
        elif kind == OTHER:
            ref = row["material_type_id"]
        else:
            ref = 0
        positions[row["event__product_id"]][(kind, ref)] = {
            name: row[name] or ZERO  # type: ignore[literal-required]
            for name in LINE_FIELDS[kind]
        }
    pool_incoming = {
        row["material_type_id"]: row["total"] or ZERO
        for row in StockEventLine.objects.filter(pool_kind=OTHER)
        .values("material_type_id")
        .annotate(total=models.Sum("d_incoming"))
    }
    for product_id, position in positions.items():
        # A product that shares a material type but never moved it still sees
        # the pool-wide incoming other products recorded.
        for material_type_id in product_material_type_ids(Product(pk=product_id)):
            position.setdefault(
                (OTHER, material_type_id), {"incoming": ZERO, "packed": ZERO}
            )
        for key, figures in position.items():
            if key[0] == OTHER:
                figures["incoming"] = pool_incoming.get(int(key[1]), ZERO)
    return positions


def check_ledger(product_ids: Iterable[int] | None = None) -> list[str]:
    """Compare the ledger with the live figures; return one message per mismatch.

    Empty means in sync. A pool the ledger has never moved reads as zero there,
    so a live figure that is non-zero with no ledger line is a mismatch too.
    """
    if product_ids is None:
        product_ids = list(Product.all_objects.values_list("pk", flat=True))
    product_ids = list(product_ids)
    live = read_positions(product_ids)
    ledger = ledger_positions(product_ids)
    problems: list[str] = []
    for product_id in product_ids:
        live_position = live.get(product_id, {})
        ledger_position = ledger.get(product_id, {})
        for key in sorted(live_position.keys() | ledger_position.keys(), key=str):
            for name in LINE_FIELDS[key[0]]:
                expected = live_position.get(key, {}).get(name, ZERO)
                recorded = ledger_position.get(key, {}).get(name, ZERO)
                if expected != recorded:
                    problems.append(
                        f"product {product_id} {StockPoolKind(key[0]).name} {key[1]} "
                        f"{name}: live {expected}, ledger {recorded}"
                    )
    return problems
