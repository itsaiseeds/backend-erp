"""Daily stock-count helpers for the ``aggregator`` sales domain.

The stock model is a **daily physical count**, not a running ledger. An admin
holding ``can_update_stock_count`` -- or a godown manager, who counts the floor
from the Android app -- uploads what is on the floor; that count is
the day's opening balance. Every day's count is kept as history; reads always
pick **one** ``snapshot_date`` (today, an explicit date, or the latest counted
date), so older days never leak into a computed figure.

Stock lives in two pools that never mix, in two tables at two grains:

* ``InventorySnapshot.bags`` - sealed whole packagings, consumed by normal
  ``OrderItem`` lines. Keyed by ``ProductPackaging``, counted in bags, the same
  unit as ``OrderItem.quantity``.
* ``LooseStockSnapshot.packets`` - stock in a packet but not in a bag, consumed
  by ``CustomOrderItem`` lines. Keyed by ``(product, packet_weight)``, because
  that is all the identity a loose packet has -- a product with a 1kg x 20 and
  a 1kg x 30 packaging has **one** pool of loose 1kg packets, not two.

A packaged order may never be filled from loose stock, and a custom order may
never break open a bag.

The two pools run on **independent date lifecycles**. The bag count is
compulsory (``is_stock_count_complete`` gates order verification) and is read
at its own latest date; the loose count is optional, written when it changes,
excluded from that gate, and read at *its* own latest date.
Because a loose count may be days old and still correct, loose figures are read
at ``loose_date(...)`` -- the latest loose snapshot date -- rather than today.

Reserved and consumed quantities are **derived from ``Order.status`` and
``DispatchEntryItem.quantity``**, never stored as their own counter. That makes
verification and dispatch inherently reversible (flip the status back and the
numbers correct themselves) and means outstanding reservations carry across
days, which a stored counter would not. A dispatch that ships less than a line
ordered leaves the gap reserved against that same order -- dispatch is
one-shot, so nothing will ship the rest later; the gap only closes when
someone corrects the order or the dispatch by hand.

**Counts are backed by raw material.** Bags and loose packets are packed out
of a product's inward raw kilograms (``InwardRawMaterial`` lots that are
``In Use`` with a reached ``effective_date``). Writing a count is how packing
is recorded, so every count write is checked against that raw pool and rolls
back when it would overdraw it. The packed kilograms are derived, never
stored: whatever the latest count holds plus whatever was dispatched *before*
that count (it left the floor but still used raw material). Lowering a count
therefore releases its kilograms back to raw automatically.

Snapshots are exposed to the frontend by their ``public_id`` (``INV-…``);
payloads never include the internal primary key.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.db.models import F, Q, Sum

from common.models import indian_now

from .models import (
    CustomOrderItem,
    DispatchEntryItem,
    InventorySnapshot,
    InwardOtherMaterial,
    InwardRawMaterial,
    LooseStockSnapshot,
    Order,
    OrderItem,
    OtherMaterialRecipe,
    OtherMaterialType,
    PackedRecipeLayer,
    Product,
    ProductPackaging,
    RawMaterialWaste,
    StatusIds,
    StockEventDetail,
    StockEventType,
    StockPoolKind,
)
from .ProductOperations import assert_products_usable

if TYPE_CHECKING:
    from authentication.models import User

# Orders holding sealed bags: verified, not yet gone.
RESERVING_STATUS_IDS = (StatusIds.CONFIRMED,)
# Orders whose bags have physically left the warehouse.
CONSUMING_STATUS_IDS = (StatusIds.DISPATCHED, StatusIds.DELIVERED)


def today() -> date:
    """Today in the project's timezone (Asia/Kolkata)."""
    return indian_now().date()


def _assert_can_update_stock_count(actor: User | None) -> None:
    """Raise unless ``actor`` may write a stock count.

    ``User.can_update_stock_count`` gates exactly this and nothing else -- in
    particular it does **not** gate order verification.
    """
    if actor is None:
        raise PermissionDenied("A user must be provided to record a stock count.")
    if actor.can_update_stock_count:
        return
    if actor.live_admin_profile is None:
        raise PermissionDenied(
            "Stock counts can only be recorded by a sales admin or a godown manager."
        )
    raise PermissionDenied(f"User '{actor}' is not allowed to update the stock count.")


# -- Writing the count --------------------------------------------------------


@transaction.atomic
def record_stock_count(
    *,
    product_packaging: ProductPackaging,
    bags: int,
    actor: User,
    snapshot_date: date | None = None,
) -> InventorySnapshot:
    """Record the count for a single packaging on ``snapshot_date``.

    Re-recording the same ``(snapshot_date, product_packaging)`` overwrites the
    earlier figures rather than adding a second row. Rejected (and rolled back)
    when the product's raw material or packing material cannot cover the bags.
    """
    from . import StockLedgerOperations

    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()
    with StockLedgerOperations.recording(
        None,
        StockEventDetail.BAG_COUNT,
        [product_packaging.product_id],
        actor=actor,
        new_bag_date=snapshot_date,
    ) as rec:
        assert_products_usable(
            [product_packaging.product_id], field="counts", action="have its stock counted"
        )
        lock_raw_pools([product_packaging.product_id])
        materials_before = _material_guard([product_packaging.product_id])
        bags_before = _bag_availability([product_packaging])
        snapshot = _write_stock_count(
            product_packaging=product_packaging,
            bags=bags,
            actor=actor,
            snapshot_date=snapshot_date,
        )
        _assert_raw_available([product_packaging.product_id])
        rec.after_sync_checks.append(lambda: _assert_material_available(materials_before))
        _assert_bags_not_overreserved(bags_before)
        rec.sources = {product_packaging.product_id: snapshot}
    return snapshot


def _write_stock_count(
    *,
    product_packaging: ProductPackaging,
    bags: int,
    actor: User,
    snapshot_date: date,
) -> InventorySnapshot:
    """Upsert one bag line. No permission or raw-material check -- callers do both.

    Takes the packaging's bag-pool lock, so a count cannot land between an
    order's availability read and its reservation.
    """
    lock_bag_pools([product_packaging])
    existing = InventorySnapshot.all_objects.filter(
        snapshot_date=snapshot_date, product_packaging=product_packaging
    ).first()
    is_new = existing is None
    snapshot = existing or InventorySnapshot(
        snapshot_date=snapshot_date,
        product_packaging=product_packaging,
        created_by=actor,
    )
    snapshot.bags = bags
    snapshot.counted_at = indian_now()
    snapshot.is_deleted = False
    snapshot.deleted_at = None
    snapshot.deleted_by = None
    snapshot.full_clean()
    snapshot.save()
    if is_new:
        previous = (
            InventorySnapshot.objects.filter(
                product_packaging=product_packaging, snapshot_date__lt=snapshot_date
            )
            .order_by("-snapshot_date")
            .first()
        )
        if previous is not None:
            copy_recipe_layers(previous, snapshot)
    return snapshot


@transaction.atomic
def record_stock_counts(
    *,
    counts: Mapping[ProductPackaging, int],
    actor: User,
    snapshot_date: date | None = None,
    carry_forward: bool = False,
    carry_frozen: bool = False,
) -> list[InventorySnapshot]:
    """Upload a whole day's bag count in one transaction.

    ``counts`` maps a ``ProductPackaging`` to its bag count::

        record_stock_counts(counts={pack_a: 400, pack_b: 10}, actor=admin)

    Loose stock is *not* recorded here -- it is a separate, optional count; see
    ``record_loose_stocks``.

    Every line is written; earlier days' counts are kept as history.

    ``carry_forward=True`` is for a **partial** upload (PATCH): when it opens a
    new date, every packaging counted on the previous latest date that the
    upload does not name gets a row on the new date too, holding its physical
    figure (last count minus what was dispatched since). Without it those
    packagings would read 0 bags on hand at the new date and silently return
    their raw and packing material. A full upload (POST) names every packaging,
    so it carries nothing. The carried rows are not returned.

    ``carry_frozen=True`` is the full-upload (POST) counterpart: a full upload
    names every *usable* packaging, but a packaging of an unusable product cannot
    be counted, so it is carried forward exactly as above -- and only it -- so
    freezing a product never moves its stock, raw material or packing material.

    The raw-material check runs once, after every line is written, so one
    upload may raise one packaging of a product and lower another: only the
    net kilograms per product must fit its raw pool. The packing-material
    check works the same way, per material type. Any shortfall rolls the
    whole upload back.
    """
    from . import StockLedgerOperations

    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()
    product_ids = {packaging.product_id for packaging in counts}
    with StockLedgerOperations.recording(
        None,
        StockEventDetail.BAG_COUNT,
        product_ids,
        actor=actor,
        new_bag_date=snapshot_date,
    ) as rec:
        assert_products_usable(product_ids, field="counts", action="have its stock counted")
        lock_raw_pools(product_ids)
        # All up front and in pk order; _write_stock_count re-takes each as a no-op.
        lock_bag_pools(counts)
        materials_before = _material_guard(product_ids)
        bags_before = _bag_availability(counts)
        if carry_forward or carry_frozen:
            carried = _carry_forward_bag_counts(
                counts, snapshot_date, actor, frozen_only=not carry_forward
            )
            rec.carried |= {
                (row.product_packaging.product_id, (StockPoolKind.BAG, row.product_packaging_id))
                for row in carried
            }

        snapshots = [
            _write_stock_count(
                product_packaging=product_packaging,
                bags=bags,
                actor=actor,
                snapshot_date=snapshot_date,
            )
            for product_packaging, bags in counts.items()
        ]
        _assert_raw_available(product_ids)
        rec.after_sync_checks.append(lambda: _assert_material_available(materials_before))
        _assert_bags_not_overreserved(bags_before)
        rec.sources = {
            snapshot.product_packaging.product_id: snapshot
            for snapshot in reversed(snapshots)
        }
    return snapshots


def _carry_forward_bag_counts(
    named: Iterable[ProductPackaging],
    snapshot_date: date,
    actor: User,
    *,
    frozen_only: bool = False,
) -> list[InventorySnapshot]:
    """Count every unnamed packaging onto a newly opened date, at its physical figure.

    Only acts when ``snapshot_date`` is later than the latest bag count date.
    Packed and available are unchanged by it: the count drops by what was
    dispatched since the last count, and those dispatches now precede the new
    count instead.

    ``frozen_only`` restricts it to packagings of unusable products (the full-upload
    case). Carrying is a system write, not a user change, so it deliberately
    bypasses the usability guard.
    """
    latest = latest_snapshot_date()
    if latest is None or snapshot_date <= latest:
        return []
    named_ids = {packaging.pk for packaging in named}
    carried = []
    rows = InventorySnapshot.objects.filter(snapshot_date=latest).exclude(
        product_packaging_id__in=named_ids
    )
    for row in rows.select_related("product_packaging__product"):
        packaging = row.product_packaging
        if packaging.is_deleted or (frozen_only and packaging.product.is_usable):
            continue
        physical = max(row.bags - consumed_bags(packaging, latest), 0)
        carried.append(
            _write_stock_count(
                product_packaging=packaging,
                bags=physical,
                actor=actor,
                snapshot_date=snapshot_date,
            )
        )
    return carried


def _carry_forward_loose_counts(
    named: Iterable[tuple[Product, Decimal]],
    snapshot_date: date,
    actor: User,
    *,
    frozen_only: bool = False,
) -> list[LooseStockSnapshot]:
    """The loose-pool counterpart of :func:`_carry_forward_bag_counts`."""
    latest = latest_loose_snapshot_date()
    if latest is None or snapshot_date <= latest:
        return []
    named_pairs = {(product.pk, Decimal(weight)) for product, weight in named}
    carried = []
    for row in LooseStockSnapshot.objects.filter(snapshot_date=latest).select_related(
        "product"
    ):
        if (row.product_id, row.packet_weight) in named_pairs or row.product.is_deleted:
            continue
        if frozen_only and row.product.is_usable:
            continue
        physical = max(
            row.packets
            - consumed_loose_packets(row.product, row.packet_weight, latest),
            0,
        )
        carried.append(
            _write_loose_stock(
                product=row.product,
                packet_weight=row.packet_weight,
                packets=physical,
                actor=actor,
                snapshot_date=snapshot_date,
            )
        )
    return carried


# -- Recipe layers ------------------------------------------------------------
#
# Packing material is spent when a packet is packed, at the recipe in force
# *then*. Each count row therefore carries ``PackedRecipeLayer`` rows -- how many
# of its packed packets were packed under which recipe -- so a later recipe
# change (delete + create) never re-values packets that are already packed.
# Layers are kept in step with each pool's packed packets by
# ``StockLedgerOperations.recording`` (:func:`add_packed_packets`,
# :func:`remove_packed_packets`, :func:`clamp_recipe_layers`), which is the one
# place a write's change in packed packets is known.

CountRow = InventorySnapshot | LooseStockSnapshot


def _layer_field(row: CountRow) -> str:
    return (
        "inventory_snapshot"
        if isinstance(row, InventorySnapshot)
        else "loose_stock_snapshot"
    )


def recipe_layers(row: CountRow):
    """``row``'s layers, oldest first."""
    return PackedRecipeLayer.objects.filter(**{_layer_field(row): row})


def copy_recipe_layers(source: CountRow, target: CountRow) -> None:
    """Give a new count row its predecessor's layers, ``opened_at`` preserved."""
    field = _layer_field(target)
    PackedRecipeLayer.objects.bulk_create(
        PackedRecipeLayer(
            **{field: target},
            material_type_id=layer.material_type_id,
            recipe_id=layer.recipe_id,
            packets=layer.packets,
            opened_at=layer.opened_at,
        )
        for layer in recipe_layers(source)
    )


def _add_layer(
    row: CountRow, material_type_id: int, recipe_id: int | None, packets: int
) -> None:
    """Add ``packets`` to the newest layer of the type if it is the same recipe."""
    newest = (
        recipe_layers(row)
        .filter(material_type_id=material_type_id)
        .order_by("-opened_at", "-id")
        .first()
    )
    if newest is not None and newest.recipe_id == recipe_id:
        newest.packets += packets
        newest.save(update_fields=["packets"])
        return
    PackedRecipeLayer.objects.create(
        **{_layer_field(row): row},
        material_type_id=material_type_id,
        recipe_id=recipe_id,
        packets=packets,
        opened_at=indian_now(),
    )


def add_packed_packets(row: CountRow, product_id: int, packet_weight, packets: int) -> None:
    """Record ``packets`` newly packed into ``row``'s pool, at today's live recipes.

    A material type that already has layers on this row but no live recipe
    for the pool any more gets a NULL-recipe layer: packed while no recipe
    existed, so it spends nothing but still counts as packed.
    """
    if packets <= 0:
        return
    covered: set[int] = set()
    for recipe in OtherMaterialRecipe.objects.filter(
        product_id=product_id, packet_weight=packet_weight
    ):
        _add_layer(row, recipe.material_type_id, recipe.pk, packets)
        covered.add(recipe.material_type_id)
    layered = set(recipe_layers(row).values_list("material_type_id", flat=True))
    for material_type_id in layered - covered:
        _add_layer(row, material_type_id, None, packets)


def remove_packed_packets(row: CountRow, packets: int) -> None:
    """Unpack ``packets`` from ``row``, newest layer first, per material type.

    Whatever a type's layers cannot cover comes off the implicit "unlayered"
    packets at the bottom -- those packed before the type's first recipe.
    """
    if packets <= 0:
        return
    for material_type_id in set(
        recipe_layers(row).values_list("material_type_id", flat=True)
    ):
        _unpack_type(row, material_type_id, packets)


def clamp_recipe_layers(row: CountRow, packed_packets: int) -> bool:
    """Enforce: per material type, layered packets never exceed packed packets.

    Returns whether any layer had to be trimmed.
    """
    totals = list(
        recipe_layers(row)
        .values("material_type_id")
        .annotate(total=Sum("packets"))
        .filter(total__gt=packed_packets)
    )
    for entry in totals:
        _unpack_type(row, entry["material_type_id"], entry["total"] - packed_packets)
    return bool(totals)


def seed_recipe_layers() -> int:
    """Seed layers for the latest count rows at the current recipes (go-live).

    Each latest bag and loose row gets one layer per live recipe of its pool,
    holding all of the pool's packed packets (count plus dispatched before it).
    Rows that already have layers are left alone. Returns the layers created.
    """
    created = 0
    bag_date = latest_snapshot_date()
    if bag_date is not None:
        bag_rows = InventorySnapshot.objects.filter(snapshot_date=bag_date)
        for bag_row in bag_rows.select_related("product_packaging"):
            if recipe_layers(bag_row).exists():
                continue
            packaging = bag_row.product_packaging
            packed = (
                bag_row.bags + _bags_dispatched_before(packaging, bag_date)
            ) * packaging.packets
            created += _seed_row(
                bag_row, packaging.product_id, packaging.packet_weight, packed
            )
    loose_snapshot_date = latest_loose_snapshot_date()
    if loose_snapshot_date is not None:
        loose_rows = LooseStockSnapshot.objects.filter(snapshot_date=loose_snapshot_date)
        for loose_row in loose_rows:
            if recipe_layers(loose_row).exists():
                continue
            packed = loose_row.packets + _loose_dispatched_before(
                loose_row.product, loose_row.packet_weight, loose_snapshot_date
            )
            created += _seed_row(
                loose_row, loose_row.product_id, loose_row.packet_weight, packed
            )
    return created


def _seed_row(row: CountRow, product_id: int, packet_weight, packed: int) -> int:
    if packed <= 0:
        return 0
    recipes = list(
        OtherMaterialRecipe.objects.filter(product_id=product_id, packet_weight=packet_weight)
    )
    PackedRecipeLayer.objects.bulk_create(
        PackedRecipeLayer(
            **{_layer_field(row): row},
            material_type_id=recipe.material_type_id,
            recipe_id=recipe.pk,
            packets=packed,
            opened_at=indian_now(),
        )
        for recipe in recipes
    )
    return len(recipes)


def _unpack_type(row: CountRow, material_type_id: int, packets: int) -> None:
    remaining = packets
    layers = recipe_layers(row).filter(material_type_id=material_type_id)
    for layer in layers.order_by("-opened_at", "-id"):
        take = min(layer.packets, remaining)
        if take == layer.packets:
            layer.delete()
        else:
            layer.packets -= take
            layer.save(update_fields=["packets"])
        remaining -= take
        if remaining == 0:
            break


# -- Counts may not undercut what is already promised --------------------------
#
# A count only ever *states* what is on the floor, so on its own it does not
# check the orders already holding that stock. These guards close that gap, the
# same way the raw and packing-material checks do: a count is refused when it
# leaves a pool's available stock negative **and lower than it was** -- so a
# pool that was already short, and a count that keeps or raises it, are never
# blocked. They run after the write, inside the same transaction, so a refusal
# rolls the whole upload back (and the ledger with it).


def _bag_availability(packagings: Iterable[ProductPackaging]) -> dict[ProductPackaging, int]:
    """Available bags of each packaging at the latest count date, before a write."""
    latest = latest_snapshot_date()
    return {packaging: available_bags(packaging, latest) for packaging in packagings}


def _loose_availability(
    pools: Iterable[tuple[Product, Decimal]],
) -> dict[tuple[Product, Decimal], int]:
    """Available loose packets of each ``(product, packet_weight)`` pool, before a write."""
    latest = latest_loose_snapshot_date()
    return {
        (product, weight): available_loose_packets(product, weight, latest)
        for product, weight in pools
    }


def _assert_bags_not_overreserved(before: Mapping[ProductPackaging, int]) -> None:
    """Raise ``ValueError`` if a bag count left a packaging short of what orders hold."""
    latest = latest_snapshot_date()
    short = []
    for packaging, was in before.items():
        now = available_bags(packaging, latest)
        if now < 0 and now < was:
            short.append(
                f"'{packaging}' would be short by {-now} bags "
                f"({reserved_bags(packaging)} reserved by orders, "
                f"{consumed_bags(packaging, latest)} already dispatched)"
            )
    if short:
        raise ValueError(
            "Cannot lower the count below what orders already hold: " + "; ".join(short) + "."
        )


def _assert_loose_not_overreserved(before: Mapping[tuple[Product, Decimal], int]) -> None:
    """Raise ``ValueError`` if a loose count left a pool short of what custom orders hold."""
    latest = latest_loose_snapshot_date()
    short = []
    for (product, weight), was in before.items():
        now = available_loose_packets(product, weight, latest)
        if now < 0 and now < was:
            short.append(
                f"'{product.name}' loose {weight}kg packets would be short by {-now} "
                f"({reserved_loose_packets(product, weight)} reserved by custom orders, "
                f"{consumed_loose_packets(product, weight, latest)} already dispatched)"
            )
    if short:
        raise ValueError(
            "Cannot lower the count below what custom orders already hold: "
            + "; ".join(short)
            + "."
        )


# -- Reading the count --------------------------------------------------------


def latest_snapshot_date() -> date | None:
    """The most recent date any stock count was recorded for."""
    return (
        InventorySnapshot.objects.order_by("-snapshot_date")
        .values_list("snapshot_date", flat=True)
        .first()
    )


def snapshot_for(snapshot_date: date | None = None):
    """Every counted line for ``snapshot_date`` (defaults to today)."""
    return InventorySnapshot.objects.filter(
        snapshot_date=snapshot_date or today()
    ).select_related("product_packaging__product")


def snapshot_line(
    product_packaging: ProductPackaging, snapshot_date: date | None = None
) -> InventorySnapshot | None:
    """The counted line for one packaging, or ``None`` if it was not counted."""
    return InventorySnapshot.objects.filter(
        snapshot_date=snapshot_date or today(),
        product_packaging=product_packaging,
    ).first()


def missing_packagings(snapshot_date: date | None = None):
    """Active packagings with no counted line for ``snapshot_date``.

    Packagings of an unusable product are left out: nobody can count them while
    the product is frozen (their last figure is carried forward onto each new
    date instead -- see ``_carry_forward_bag_counts``), so they must not block
    the day's count from being complete.
    """
    counted = snapshot_for(snapshot_date).values_list("product_packaging_id", flat=True)
    return ProductPackaging.objects.exclude(id__in=counted).filter(product__is_usable=True)


def is_stock_count_complete(snapshot_date: date | None = None) -> bool:
    """Whether the day's count covers **every** active packaging.

    This is what "the stock count has been uploaded for the day" means: the
    count is for all the products, so a partial upload does not open
    verification.

    Covers **bags only**. The loose count is optional by design, so a missing
    or stale ``LooseStockSnapshot`` never blocks verification.
    """
    return not missing_packagings(snapshot_date).exists()


# -- Deriving position: sealed bags ----------------------------------------


def _bag_demand(
    product_packaging: ProductPackaging, order_filter: dict, *conditions: Q
) -> int:
    """Sum ``OrderItem.quantity`` for this packaging across matching orders.

    ``OrderItem.objects`` hides deleted lines, but a lookup spanning to the
    order does not apply the order's manager, so deleted orders are excluded
    explicitly. That is always right because an order holding stock (CONFIRMED
    and later) cannot be deleted -- see ``Order.guard_soft_delete``.
    """
    total = OrderItem.objects.filter(
        *conditions,
        product_packaging=product_packaging,
        order__is_deleted=False,
        **order_filter,
    ).aggregate(total=Sum("quantity"))["total"]
    return total or 0


def _dispatched_bag_demand(
    product_packaging: ProductPackaging, order_filter: dict, *conditions: Q
) -> int:
    """Sum ``DispatchEntryItem.quantity`` -- what actually shipped -- for matching orders.

    Unlike ``_bag_demand``, this is the truth for what left the warehouse: a
    dispatch may ship fewer bags than a line ordered (see ``DispatchEntryItem``),
    so ``OrderItem.quantity`` alone would overstate it.
    """
    total = DispatchEntryItem.objects.filter(
        *conditions,
        product_packaging=product_packaging,
        **{f"dispatch_entry__{key}": value for key, value in order_filter.items()},
    ).aggregate(total=Sum("quantity"))["total"]
    return total or 0


def _bag_counted_at(
    product_packaging: ProductPackaging, snapshot_date: date
) -> datetime | None:
    """When one packaging's line for ``snapshot_date`` was counted, if it was."""
    return (
        InventorySnapshot.objects.filter(
            snapshot_date=snapshot_date, product_packaging=product_packaging
        )
        .values_list("counted_at", flat=True)
        .first()
    )


def _dispatch_conditions(
    prefix: str, snapshot_date: date, counted_at: datetime | None, *, after_count: bool
) -> list[Q]:
    """Q condition(s) selecting dispatches on the correct side of one count.

    Every dispatch -- bag or loose, agency or private -- writes exactly one
    ``DispatchEntry``, so its ``dispatched_at`` is the single source of truth
    for when it happened; ``prefix`` is how far the summed model (an
    ``OrderItem``-like line) is from that entry (``""`` for ``DispatchEntryItem``
    itself, ``"custom_order"`` from a ``CustomOrderItem``).

    A dispatch on any other day is decided by the day alone. The count's *own*
    day is the ambiguous one: a dispatch recorded before ``counted_at`` is
    already missing from the figure just written and must not be subtracted a
    second time; one recorded after it is still baked into that stale figure
    and must be. When ``counted_at`` is unknown (no snapshot for this exact
    line on this date), the whole day falls on the ``after_count`` side --
    the old, coarser assumption that a stale count predates its day's
    dispatches unless a precise count says otherwise.
    """
    field = (
        f"{prefix}__dispatch_entry__dispatched_at" if prefix else "dispatch_entry__dispatched_at"
    )
    if after_count:
        conditions = [Q(**{f"{field}__date__gt": snapshot_date})]
        same_day = Q(**{f"{field}__date": snapshot_date})
        if counted_at is not None:
            same_day &= Q(**{f"{field}__gte": counted_at})
        conditions.append(same_day)
        return conditions

    conditions = [Q(**{f"{field}__date__lt": snapshot_date})]
    if counted_at is not None:
        conditions.append(
            Q(**{f"{field}__date": snapshot_date, f"{field}__lt": counted_at})
        )
    return conditions


def reserved_bags(product_packaging: ProductPackaging) -> int:
    """Bags spoken for: verified orders not yet dispatched, plus shortfalls on ones that are.

    A dispatched order's line still counts here for whatever it ordered but
    did not ship -- dispatch is one-shot, so that gap has no later shipment to
    close it and stays reserved against the order until someone corrects it by
    hand (edit the line down, or revert and re-record the dispatch).
    """
    held_by_confirmed = _bag_demand(
        product_packaging, {"order__status_id__in": RESERVING_STATUS_IDS}
    )
    ordered_on_dispatched = _bag_demand(
        product_packaging, {"order__status_id__in": CONSUMING_STATUS_IDS}
    )
    shipped = _dispatched_bag_demand(
        product_packaging, {"order__status_id__in": CONSUMING_STATUS_IDS}
    )
    return held_by_confirmed + (ordered_on_dispatched - shipped)


def consumed_bags(
    product_packaging: ProductPackaging, snapshot_date: date | None = None
) -> int:
    """Bags dispatched after ``snapshot_date``'s count was taken.

    Dispatches predating the count already left the warehouse before it was
    taken, so they are absent from the counted figure and must not be
    subtracted a second time -- including earlier on the count's own day (see
    ``_dispatch_conditions``). Reads ``DispatchEntryItem.quantity``, not the
    order line's quantity, so a partial dispatch is not overcounted here (its
    unshipped remainder is reserved instead -- see ``reserved_bags``).
    """
    snapshot_date = snapshot_date or today()
    counted_at = _bag_counted_at(product_packaging, snapshot_date)
    base = {"order__status_id__in": CONSUMING_STATUS_IDS}
    return sum(
        _dispatched_bag_demand(product_packaging, base, condition)
        for condition in _dispatch_conditions(
            "", snapshot_date, counted_at, after_count=True
        )
    )


def on_hand_bags(
    product_packaging: ProductPackaging, snapshot_date: date | None = None
) -> int:
    """The raw physical count for the day (0 when the packaging was not counted).

    This is the stale, as-counted figure -- it still includes bags dispatched
    later the same day. It is not what a stock-position response calls
    "on hand" (that's ``available + reserved``, computed in ``stock_position``);
    this one is only for internal use, e.g. ``available_bags`` and
    ``raw_bagged_kg``.
    """
    line = snapshot_line(product_packaging, snapshot_date)
    return line.bags if line else 0


def available_bags(
    product_packaging: ProductPackaging, snapshot_date: date | None = None
) -> int:
    """Sealed bags still sellable: counted minus reserved minus dispatched."""
    snapshot_date = snapshot_date or today()
    return (
        on_hand_bags(product_packaging, snapshot_date)
        - reserved_bags(product_packaging)
        - consumed_bags(product_packaging, snapshot_date)
    )


# -- Deriving position: loose packets (per PRODUCT + PACKET WEIGHT) -------------
#
# "Loose" means in a packet but not in a bag. Such a packet is identified by its
# product and its weight and nothing else -- which packaging it *would* have been
# bagged into is not a property it has, and ``ProductPackaging.packets`` (how
# many packets go in a bag) says nothing about it. So the loose pool is keyed by
# ``(product, packet_weight)``: a product with a 1kg x 20 and a 1kg x 30
# packaging has one pool of loose 1kg packets, not two.
#
# ``CustomOrderItem`` names the same pair, so demand compares directly with no
# conversion. The reserve/consume logic mirrors the bag pool exactly -- keyed off
# the custom order's status and dispatch dates -- so it is reversible for free
# and a dispatch predating the count is never subtracted twice.


def latest_loose_snapshot_date() -> date | None:
    """The most recent date any loose count was recorded for."""
    return (
        LooseStockSnapshot.objects.order_by("-snapshot_date")
        .values_list("snapshot_date", flat=True)
        .first()
    )


def loose_date(snapshot_date: date | None = None) -> date:
    """Resolve the date loose figures are read at.

    Explicit date, else the latest loose count, else today. Unlike bags, loose
    stock has no daily completeness gate, so a count may be days old and still
    be the truth -- defaulting to ``today()`` would silently report zero the
    morning after every count.
    """
    return snapshot_date or latest_loose_snapshot_date() or today()


def product_loose_weights(product: Product):
    """The distinct packet weights this product is packed in.

    The universe of valid loose lines for a product: a weight the business
    actually packs, taken from its packagings.
    """
    return (
        ProductPackaging.objects.filter(product=product)
        .values_list("packet_weight", flat=True)
        .distinct()
        .order_by("packet_weight")
    )


@transaction.atomic
def record_loose_stock(
    *,
    product: Product,
    packet_weight,
    packets: int,
    actor: User,
    snapshot_date: date | None = None,
) -> LooseStockSnapshot:
    """Record the loose count for one ``(product, packet_weight)`` on ``snapshot_date``.

    Re-recording the same ``(snapshot_date, product, packet_weight)`` overwrites
    the earlier figure rather than adding a second row. Rejected (and rolled
    back) when the product's raw material or packing material cannot cover
    the packets.
    """
    from . import StockLedgerOperations

    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()
    with StockLedgerOperations.recording(
        None,
        StockEventDetail.LOOSE_COUNT,
        [product.id],
        actor=actor,
        new_loose_date=snapshot_date,
    ) as rec:
        assert_products_usable([product.id], field="counts", action="have its stock counted")
        lock_raw_pools([product.id])
        materials_before = _material_guard([product.id])
        loose_before = _loose_availability([(product, packet_weight)])
        snapshot = _write_loose_stock(
            product=product,
            packet_weight=packet_weight,
            packets=packets,
            actor=actor,
            snapshot_date=snapshot_date,
        )
        _assert_raw_available([product.id])
        rec.after_sync_checks.append(lambda: _assert_material_available(materials_before))
        _assert_loose_not_overreserved(loose_before)
        rec.sources = {product.id: snapshot}
    return snapshot


def _write_loose_stock(
    *,
    product: Product,
    packet_weight,
    packets: int,
    actor: User,
    snapshot_date: date,
) -> LooseStockSnapshot:
    """Upsert one loose line. No permission or raw-material check -- callers do both.

    Takes the product's loose-pool lock, so a count cannot land between a
    custom order's availability read and its reservation.
    """
    lock_loose_pools([product.id])
    existing_loose = LooseStockSnapshot.all_objects.filter(
        snapshot_date=snapshot_date, product=product, packet_weight=packet_weight
    ).first()
    is_new = existing_loose is None
    snapshot = existing_loose or LooseStockSnapshot(
        snapshot_date=snapshot_date,
        product=product,
        packet_weight=packet_weight,
        created_by=actor,
    )
    snapshot.packets = packets
    snapshot.counted_at = indian_now()
    snapshot.is_deleted = False
    snapshot.deleted_at = None
    snapshot.deleted_by = None
    snapshot.full_clean()
    snapshot.save()
    if is_new:
        previous = (
            LooseStockSnapshot.objects.filter(
                product=product,
                packet_weight=packet_weight,
                snapshot_date__lt=snapshot_date,
            )
            .order_by("-snapshot_date")
            .first()
        )
        if previous is not None:
            copy_recipe_layers(previous, snapshot)
    return snapshot


@transaction.atomic
def record_loose_stocks(
    *,
    counts: Mapping[tuple[Product, Decimal], int],
    actor: User,
    snapshot_date: date | None = None,
    carry_forward: bool = False,
    carry_frozen: bool = False,
) -> list[LooseStockSnapshot]:
    """Upload a whole loose count in one transaction.

    ``counts`` maps a ``(product, packet_weight)`` pair to its packet count::

        record_loose_stocks(counts={(product, Decimal("1.000")): 12}, actor=admin)

    Unlike the bag count this is **optional** -- nothing requires it to be
    written daily, or at all. Like the bag count, the net kilograms per product
    must fit its raw pool, and the net units per packing material its
    material pool, or the whole upload rolls back.

    ``carry_forward=True`` carries every loose pool the upload does not name
    onto a newly opened date, exactly as :func:`record_stock_counts` does.
    ``carry_frozen=True`` carries only the pools of unusable products (the full-upload
    case), as there.
    """
    from . import StockLedgerOperations

    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()
    product_ids = {product.id for product, _ in counts}
    with StockLedgerOperations.recording(
        None,
        StockEventDetail.LOOSE_COUNT,
        product_ids,
        actor=actor,
        new_loose_date=snapshot_date,
    ) as rec:
        assert_products_usable(product_ids, field="counts", action="have its stock counted")
        lock_raw_pools(product_ids)
        # All up front and in pk order; _write_loose_stock re-takes each as a no-op.
        lock_loose_pools(product_ids)
        materials_before = _material_guard(product_ids)
        loose_before = _loose_availability(counts)
        if carry_forward or carry_frozen:
            carried = _carry_forward_loose_counts(
                counts, snapshot_date, actor, frozen_only=not carry_forward
            )
            rec.carried |= {
                (
                    row.product_id,
                    (StockPoolKind.LOOSE, row.packet_weight.quantize(Decimal("0.001"))),
                )
                for row in carried
            }

        snapshots = [
            _write_loose_stock(
                product=product,
                packet_weight=packet_weight,
                packets=packets,
                actor=actor,
                snapshot_date=snapshot_date,
            )
            for (product, packet_weight), packets in counts.items()
        ]
        _assert_raw_available(product_ids)
        rec.after_sync_checks.append(lambda: _assert_material_available(materials_before))
        _assert_loose_not_overreserved(loose_before)
        rec.sources = {
            snapshot.product_id: snapshot for snapshot in reversed(snapshots)
        }
    return snapshots


def loose_lines(snapshot_date: date | None = None):
    """Every counted loose line for the effective loose date."""
    return LooseStockSnapshot.objects.filter(
        snapshot_date=loose_date(snapshot_date)
    ).select_related("product")


def loose_line(
    product: Product, packet_weight, snapshot_date: date | None = None
) -> LooseStockSnapshot | None:
    """The counted loose line for one pool, or ``None`` if it was not counted."""
    return LooseStockSnapshot.objects.filter(
        snapshot_date=loose_date(snapshot_date),
        product=product,
        packet_weight=packet_weight,
    ).first()


def _loose_demand(
    product: Product, packet_weight, order_filter: dict, *conditions: Q
) -> int:
    """Sum ``CustomOrderItem.packets`` for this pool across matching custom orders.

    Deleted custom orders are excluded explicitly, as in ``_bag_demand``.
    """
    total = CustomOrderItem.objects.filter(
        *conditions,
        product=product,
        packet_weight=packet_weight,
        custom_order__is_deleted=False,
        **order_filter,
    ).aggregate(total=Sum("packets"))["total"]
    return total or 0


def _loose_counted_at(
    product: Product, packet_weight, snapshot_date: date
) -> datetime | None:
    """When one loose pool's line for ``snapshot_date`` was counted, if it was."""
    return (
        LooseStockSnapshot.objects.filter(
            snapshot_date=snapshot_date, product=product, packet_weight=packet_weight
        )
        .values_list("counted_at", flat=True)
        .first()
    )


def reserved_loose_packets(product: Product, packet_weight) -> int:
    """Loose packets spoken for by verified custom orders not yet dispatched."""
    return _loose_demand(
        product, packet_weight, {"custom_order__status_id__in": RESERVING_STATUS_IDS}
    )


def consumed_loose_packets(
    product: Product, packet_weight, snapshot_date: date | None = None
) -> int:
    """Loose packets dispatched by custom orders after the count was taken.

    Dispatches predating the count already left the warehouse before it was
    taken, so they are absent from the counted figure and must not be
    subtracted a second time -- including earlier on the count's own day (see
    ``_dispatch_conditions``).
    """
    snapshot_date = loose_date(snapshot_date)
    counted_at = _loose_counted_at(product, packet_weight, snapshot_date)
    base = {"custom_order__status_id__in": CONSUMING_STATUS_IDS}
    return sum(
        _loose_demand(product, packet_weight, base, condition)
        for condition in _dispatch_conditions(
            "custom_order", snapshot_date, counted_at, after_count=True
        )
    )


def on_hand_loose_packets(
    product: Product, packet_weight, snapshot_date: date | None = None
) -> int:
    """The raw physical count for one ``(product, packet_weight)``.

    A single row lookup, not a sum across a product's packagings: the pool *is*
    the pair. Like ``on_hand_bags``, this is the stale as-counted figure for
    internal use only -- see ``loose_stock_position`` for the live "on hand".
    """
    line = loose_line(product, packet_weight, snapshot_date)
    return line.packets if line else 0


def available_loose_packets(
    product: Product, packet_weight, snapshot_date: date | None = None
) -> int:
    """Loose packets of one pool still sellable. Never touched by packaged orders."""
    snapshot_date = loose_date(snapshot_date)
    return (
        on_hand_loose_packets(product, packet_weight, snapshot_date)
        - reserved_loose_packets(product, packet_weight)
        - consumed_loose_packets(product, packet_weight, snapshot_date)
    )


# -- Raw material backing ------------------------------------------------
#
# Bags and loose packets are packed out of a product's inward raw kilograms --
# ``InwardRawMaterial`` lots that are ``In Use`` with a reached
# ``effective_date`` (the same pool ``InwardOperations.raw_incoming_stock``
# reports). Every count write below is checked against it: kilograms spent on
# a bag or loose count can never exceed what has come in, and lowering a count
# releases its kilograms straight back to raw. Nothing is stored -- the spent
# figure is derived the same way ``consumed_bags``/``consumed_loose_packets``
# derive dispatches, from the current count plus whatever left the floor
# before that count was taken. Raw material written off as waste
# (``RawMaterialWaste``) is spent from the same pool.


def raw_inward_kg(product: Product, as_of: date | None = None) -> Decimal:
    """In-use raw kilograms of ``product`` with a reached effective date.

    The same filter as one product's line in
    ``InwardOperations.raw_incoming_stock`` -- the pool a count's bags and
    loose packets are packed from.
    """
    as_of = as_of or today()
    total = InwardRawMaterial.objects.filter(
        product=product,
        effective_date__isnull=False,
        effective_date__lte=as_of,
        status_id=StatusIds.IN_USE.value,
    ).aggregate(total=Sum("quantity_kg"))["total"]
    return total or Decimal("0")


def lock_raw_pools(product_ids) -> None:
    """Lock ``product_ids``' in-use raw lots for the rest of this transaction.

    Must run inside ``@transaction.atomic``, before a count is written, so two
    concurrent uploads for the same product cannot both spend the same
    kilograms past each other.
    """
    if not product_ids:
        return
    # Ordered, so every caller acquires the same rows in the same order and two
    # of them can never each hold a lot the other is waiting for.
    list(
        InwardRawMaterial.objects.select_for_update()
        .filter(product_id__in=product_ids, status_id=StatusIds.IN_USE.value)
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def lock_bag_pools(packagings: Iterable[ProductPackaging]) -> None:
    """Lock ``packagings``' rows for the rest of this transaction.

    Bag availability is derived at read time (counted - reserved - consumed),
    so there is no stock row to lock. The ``ProductPackaging`` row stands in as
    the per-bag mutex instead: every writer that reads a bag pool and then
    changes it -- verifying or editing a confirmed order, writing a count --
    takes this lock first, so two of them can never both read the same
    "available" figure and together spend more bags than exist.

    Must run inside ``@transaction.atomic``. Rows are locked in pk order so two
    callers needing overlapping packagings cannot deadlock. Re-locking a row
    this transaction already holds is a no-op.
    """
    ids = sorted({packaging.pk for packaging in packagings})
    if not ids:
        return
    list(
        ProductPackaging.all_objects.select_for_update()
        .filter(pk__in=ids)
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def lock_loose_pools(product_ids: Iterable[int]) -> None:
    """Lock the ``Product`` rows whose loose pools this transaction will spend.

    The loose-packet counterpart of :func:`lock_bag_pools`. A loose pool is
    keyed by ``(product, packet_weight)`` and has no row of its own, so the
    product row is the mutex: coarser than one pool, but every weight of a
    product is counted and spent by the same few writers, so it costs nothing
    in practice. Same contract: inside ``@transaction.atomic``, pk order.
    """
    ids = sorted(set(product_ids))
    if not ids:
        return
    list(
        Product.all_objects.select_for_update()
        .filter(pk__in=ids)
        .order_by("pk")
        .values_list("pk", flat=True)
    )


def _bags_dispatched_before(
    product_packaging: ProductPackaging, before: date | None
) -> int:
    """Bags of ``product_packaging`` actually shipped strictly before ``before``.

    Those bags already left the floor before the count ``before`` names, so
    they carry no on-hand figure any more -- but they were packed from raw
    material and must still count as spent. Reads ``DispatchEntryItem.quantity``
    so an unshipped remainder of a partial dispatch (still sitting on the floor,
    still reserved) is not mistaken for spent raw material. ``before=None`` (no
    bag count has ever been taken) counts every dispatch ever made.
    """
    base = {"order__status_id__in": CONSUMING_STATUS_IDS}
    if before is None:
        return _dispatched_bag_demand(product_packaging, base)
    counted_at = _bag_counted_at(product_packaging, before)
    return sum(
        _dispatched_bag_demand(product_packaging, base, condition)
        for condition in _dispatch_conditions("", before, counted_at, after_count=False)
    )


def _loose_dispatched_before(
    product: Product, packet_weight, before: date | None
) -> int:
    """Loose packets of ``(product, packet_weight)`` dispatched before ``before``.

    The loose-pool counterpart of ``_bags_dispatched_before``.
    """
    base = {"custom_order__status_id__in": CONSUMING_STATUS_IDS}
    if before is None:
        return _loose_demand(product, packet_weight, base)
    counted_at = _loose_counted_at(product, packet_weight, before)
    return sum(
        _loose_demand(product, packet_weight, base, condition)
        for condition in _dispatch_conditions(
            "custom_order", before, counted_at, after_count=False
        )
    )


def raw_bagged_kg(product: Product) -> Decimal:
    """Raw kilograms currently spent on ``product``'s bags, every packaging summed.

    Per packaging: the latest bag count, plus bags already dispatched before
    that count was taken -- gone from the floor, but still packed from raw
    material, so still spent.
    """
    snapshot_date = latest_snapshot_date()
    total = Decimal("0")
    for packaging in ProductPackaging.objects.filter(product=product):
        bags = on_hand_bags(packaging, snapshot_date) + _bags_dispatched_before(
            packaging, snapshot_date
        )
        total += bags * packaging.total_weight
    return total


def raw_loose_kg(product: Product) -> Decimal:
    """Raw kilograms currently spent on ``product``'s loose packets.

    Mirrors ``raw_bagged_kg`` for the loose pool, one packet weight at a time.
    """
    snapshot_date = latest_loose_snapshot_date()
    total = Decimal("0")
    for weight in product_loose_weights(product):
        packets = on_hand_loose_packets(
            product, weight, snapshot_date
        ) + _loose_dispatched_before(product, weight, snapshot_date)
        total += packets * weight
    return total


def raw_wasted_kg(product: Product) -> Decimal:
    """Raw kilograms of ``product`` written off as waste (live rows only).

    Undated: every waste row counts the moment it exists and stops counting
    when it is soft-deleted (``RawMaterialWaste.objects`` hides deleted rows).
    """
    total = RawMaterialWaste.objects.filter(product=product).aggregate(
        total=Sum("quantity_kg")
    )["total"]
    return total or Decimal("0.000")


def raw_available_kg(product: Product) -> Decimal:
    """Raw kilograms of ``product`` not yet packed into a bag or loose packet.

    ``inward - bagged - loose - wasted``. Writing a bag or loose count, or a
    waste entry, is rejected when it would push this negative -- see
    ``_assert_raw_available``. Only ``In Use`` lots feed ``inward``, so a
    ``Rejected`` lot never makes waste or packing possible.
    """
    return (
        raw_inward_kg(product)
        - raw_bagged_kg(product)
        - raw_loose_kg(product)
        - raw_wasted_kg(product)
    )


def _assert_raw_available(product_ids) -> None:
    """Raise unless every product in ``product_ids`` still has raw kg >= 0.

    Called after a count write, inside the same transaction as the write, so
    a shortfall rolls the whole write back (see ``record_stock_counts`` /
    ``record_loose_stocks``). Raises plain ``ValueError`` -- callers (the
    update-stock views) catch it and turn it into a 400, the same convention
    ``InwardOperations.assert_raw_status_transition`` uses.
    """
    for product in Product.objects.filter(id__in=product_ids):
        available = raw_available_kg(product)
        if available < 0:
            raise ValueError(
                f"Not enough raw material for '{product.name}': short by "
                f"{-available} kg."
            )


@transaction.atomic
def record_raw_waste(
    *, product: Product, quantity_kg: Decimal, reason: str, actor: User
) -> RawMaterialWaste:
    """Write off ``quantity_kg`` of ``product``'s raw material as waste.

    Takes the product's raw-pool lock first, so a concurrent count cannot spend
    the same kilograms. Rejected (and rolled back) with ``ValueError`` when
    the product has fewer unpacked raw kilograms than the waste -- the same
    convention the count writers use, which the view turns into a 400.
    """
    from . import StockLedgerOperations

    with StockLedgerOperations.recording(
        StockEventType.RAW_WASTED,
        StockEventDetail.WASTE_RECORDED,
        [product.id],
        actor=actor,
    ) as rec:
        assert_products_usable([product.id], action="have waste recorded")
        lock_raw_pools([product.id])
        waste = RawMaterialWaste.objects.create(
            product=product,
            quantity_kg=quantity_kg,
            reason=reason.strip(),
            created_by=actor,
        )
        _assert_raw_available([product.id])
        rec.source = waste
    return waste


@transaction.atomic
def update_raw_waste(
    entry: RawMaterialWaste,
    *,
    actor: User,
    quantity_kg: Decimal | None = None,
    reason: str | None = None,
) -> RawMaterialWaste:
    """Correct a waste row's kilograms and/or reason; only what is passed changes.

    The product is not editable: moving waste to another product is a delete
    and a fresh record, so each product's raw pool is only ever touched by the
    row that belongs to it. Takes the same locks as ``record_raw_waste`` and
    re-checks the pool afterwards, so raising ``quantity_kg`` beyond the
    product's unpacked raw kilograms is rejected (and rolled back) with
    ``ValueError`` -- the view turns it into a 400. Lowering it only gives
    kilograms back. The stock ledger records the change as ``WASTE_EDITED``.
    """
    from . import StockLedgerOperations

    with StockLedgerOperations.recording(
        StockEventType.RAW_WASTED,
        StockEventDetail.WASTE_EDITED,
        [entry.product_id],
        actor=actor,
        source=entry,
    ):
        assert_products_usable([entry.product_id], action="have its waste entry edited")
        lock_raw_pools([entry.product_id])
        entry = RawMaterialWaste.objects.select_for_update().get(pk=entry.pk)
        changed = []
        if quantity_kg is not None:
            entry.quantity_kg = quantity_kg
            changed.append("quantity_kg")
        if reason is not None:
            entry.reason = reason.strip()
            changed.append("reason")
        if changed:
            entry.full_clean()
            entry.save(update_fields=[*changed, "updated_at"])
            _assert_raw_available([entry.product_id])
    return entry


# -- Packing (other) material backing -----------------------------------------
#
# Every packet also uses packing material -- leaflets, covers -- per the
# product's ``OtherMaterialRecipe`` for its packet weight: ``recipe.quantity``
# units of the material type per packet. The pool is the **configuration**
# ``(product, packet weight, material type)``: an inward lot is booked against
# a recipe and only backs packets of that recipe's configuration. Spent
# material is derived from the recipe layers of the packets currently packed,
# each valued at the recipe frozen on it.


def packed_packets(product: Product) -> dict[Decimal, int]:
    """Packets of ``product`` currently packed, per packet weight.

    The packet counterpart of ``raw_bagged_kg`` + ``raw_loose_kg``, with the
    same terms: each packaging's latest bag count plus bags dispatched before
    it (times packets per bag), and each loose pool's latest count plus loose
    packets dispatched before it.
    """
    packed: dict[Decimal, int] = {}
    snapshot_date = latest_snapshot_date()
    for packaging in ProductPackaging.objects.filter(product=product):
        bags = on_hand_bags(packaging, snapshot_date) + _bags_dispatched_before(
            packaging, snapshot_date
        )
        weight = packaging.packet_weight
        packed[weight] = packed.get(weight, 0) + bags * packaging.packets
    loose_snapshot_date = latest_loose_snapshot_date()
    for weight in product_loose_weights(product):
        packets = on_hand_loose_packets(
            product, weight, loose_snapshot_date
        ) + _loose_dispatched_before(product, weight, loose_snapshot_date)
        packed[weight] = packed.get(weight, 0) + packets
    return packed


# A packing-material stock: material is printed for one product and one packet
# size, so each ``(product, packet weight, material type)`` is its own pool.
MaterialKey = tuple[int, Decimal, int]


def _narrow_keys(
    query: models.QuerySet,
    prefix: str,
    keys: Iterable[MaterialKey] | None,
    material_type_ids: Iterable[int] | None,
) -> models.QuerySet:
    """Narrow ``query`` to the products and material types of ``keys``.

    A superset in SQL (products x types); callers drop the rest in Python.
    ``prefix`` is the path from ``query``'s model to its recipe.
    """
    if keys is not None:
        keys = list(keys)
        query = query.filter(
            **{
                f"{prefix}product_id__in": {key[0] for key in keys},
                f"{prefix}material_type_id__in": {key[2] for key in keys},
            }
        )
    if material_type_ids is not None:
        query = query.filter(
            **{f"{prefix}material_type_id__in": list(material_type_ids)}
        )
    return query


def _keyed_totals(
    rows: Iterable[tuple[int, Decimal, int, Decimal]],
    keys: Iterable[MaterialKey] | None,
) -> dict[MaterialKey, Decimal]:
    wanted = set(keys) if keys is not None else None
    totals: dict[MaterialKey, Decimal] = {}
    for product_id, weight, material_type_id, total in rows:
        key = (product_id, Decimal(weight), material_type_id)
        if wanted is None or key in wanted:
            totals[key] = total
    return totals


def other_material_inward(
    keys: Iterable[MaterialKey] | None = None,
    as_of: date | None = None,
    *,
    material_type_ids: Iterable[int] | None = None,
) -> dict[MaterialKey, Decimal]:
    """Units received per configuration, over lots with a reached effective date.

    The configuration is read from the lot's recipe. Lots booked against a
    since-replaced (soft-deleted) recipe still count toward the same
    configuration, whichever recipe version brought the stock in.
    """
    as_of = as_of or today()
    query = InwardOtherMaterial.objects.filter(
        effective_date__isnull=False, effective_date__lte=as_of
    )
    query = _narrow_keys(query, "recipe__", keys, material_type_ids)
    rows = (
        query.values("recipe__product_id", "recipe__packet_weight", "recipe__material_type_id")
        .annotate(total=Sum("quantity"))
        .values_list(
            "recipe__product_id", "recipe__packet_weight", "recipe__material_type_id", "total"
        )
    )
    return _keyed_totals(rows, keys)


def other_material_used(
    keys: Iterable[MaterialKey] | None = None,
    *,
    product: Product | None = None,
    material_type_ids: Iterable[int] | None = None,
) -> dict[MaterialKey, Decimal]:
    """Units per configuration spent on the packets currently packed.

    Read from the recipe layers of the latest bag and loose count rows: each
    layer charges ``recipe.quantity`` per packet it holds, at the recipe that was
    live when those packets were packed, to that recipe's configuration. A
    NULL-recipe layer spends nothing. ``product`` narrows it to one product's
    own usage.
    """
    layers = PackedRecipeLayer.objects.filter(recipe__isnull=False)
    layers = _narrow_keys(layers, "recipe__", keys, material_type_ids)
    bag_date = latest_snapshot_date()
    loose_snapshot_date = latest_loose_snapshot_date()
    bag_rows = Q(
        inventory_snapshot__is_deleted=False,
        inventory_snapshot__snapshot_date=bag_date,
    )
    loose_rows = Q(
        loose_stock_snapshot__is_deleted=False,
        loose_stock_snapshot__snapshot_date=loose_snapshot_date,
    )
    if product is not None:
        bag_rows &= Q(inventory_snapshot__product_packaging__product=product)
        loose_rows &= Q(loose_stock_snapshot__product=product)
    if bag_date is None:
        bag_rows = Q(pk__in=[])
    if loose_snapshot_date is None:
        loose_rows = Q(pk__in=[])
    rows = (
        layers.filter(bag_rows | loose_rows)
        .values(
            "recipe__product_id", "recipe__packet_weight", "recipe__material_type_id"
        )
        .annotate(total=Sum(F("recipe__quantity") * F("packets")))
        .values_list(
            "recipe__product_id", "recipe__packet_weight", "recipe__material_type_id", "total"
        )
    )
    return _keyed_totals(rows, keys)


def other_material_available(keys: Iterable[MaterialKey]) -> dict[MaterialKey, Decimal]:
    """``inward - used`` for each of ``keys``."""
    keys = list(keys)
    inward = other_material_inward(keys)
    used = other_material_used(keys)
    return {
        key: inward.get(key, Decimal("0")) - used.get(key, Decimal("0"))
        for key in keys
    }


def material_keys(product_ids: Iterable[int]) -> set[MaterialKey]:
    """Every configuration of ``product_ids``, deleted recipes included."""
    return {
        (recipe.product_id, Decimal(recipe.packet_weight), recipe.material_type_id)
        for recipe in OtherMaterialRecipe.all_objects.filter(
            product_id__in=list(product_ids)
        )
    }


def material_label(
    key: MaterialKey,
    products: Mapping[int, Product],
    materials: Mapping[int, OtherMaterialType],
) -> str:
    """``'cover' for 'P' 1.500kg``: names the configuration in an error."""
    product_id, weight, material_type_id = key
    return (
        f"'{materials[material_type_id].name}' for "
        f"'{products[product_id].name}' {Decimal(weight):.3f}kg"
    )


def _material_labels(keys: Iterable[MaterialKey]) -> dict[MaterialKey, str]:
    keys = list(keys)
    products = Product.all_objects.in_bulk({key[0] for key in keys})
    materials = OtherMaterialType.all_objects.in_bulk({key[2] for key in keys})
    return {key: material_label(key, products, materials) for key in keys}


def _lock_materials(product_ids, material_type_ids: Iterable[int] = ()) -> list[int]:
    """Lock the material types ``product_ids``' recipes use, plus ``material_type_ids``.

    Locks stay per material type, coarser than the per-configuration figures but
    correct. Rows are locked in pk order, so two writers sharing a material
    cannot both spend its last units. Deleted recipes count: their lots and
    layers still charge their configuration. Returns the locked ids.
    """
    locked = sorted(
        set(
            OtherMaterialRecipe.all_objects.filter(product_id__in=product_ids).values_list(
                "material_type_id", flat=True
            )
        )
        | set(material_type_ids)
    )
    list(
        OtherMaterialType.all_objects.select_for_update()
        .filter(pk__in=locked)
        .order_by("pk")
        .values_list("pk", flat=True)
    )
    return locked


def _material_guard(product_ids) -> dict[MaterialKey, Decimal]:
    """Lock the packing materials ``product_ids`` use; return their availability.

    Called before a count write, inside its transaction. The returned figures,
    one per configuration, are what :func:`_assert_material_available` compares
    the write against.
    """
    product_ids = list(product_ids)
    _lock_materials(product_ids)
    return other_material_available(material_keys(product_ids))


def guard_stock_deletion(
    perform: Callable[[], None],
    *,
    product_ids: Iterable[int] = (),
    packagings: Iterable[ProductPackaging] = (),
    loose_pools: Iterable[tuple[Product, Decimal]] = (),
    extra_material_keys: Iterable[MaterialKey] = (),
    ledger: tuple[StockEventType, StockEventDetail, models.Model] | None = None,
) -> None:
    """Run ``perform`` -- soft-deleting a count line or an inward lot -- or refuse it.

    ``ledger`` is ``(event_type, detail, source)``: the stock ledger records the
    deletion as one event for ``source`` (the row being deleted), attributed to
    whoever ``source.deleted_by`` ends up being. See :func:`_guard_stock_deletion`
    for the guard itself.
    """
    from . import StockLedgerOperations

    product_ids = set(product_ids)
    packagings = list(packagings)
    loose_pools = list(loose_pools)
    if ledger is None:
        _guard_stock_deletion(
            perform,
            product_ids=product_ids,
            packagings=packagings,
            loose_pools=loose_pools,
            extra_material_keys=extra_material_keys,
        )
        return
    event_type, detail, source = ledger
    tracked = (
        product_ids
        | {packaging.product_id for packaging in packagings}
        | {product.id for product, _ in loose_pools}
    )
    with StockLedgerOperations.recording(
        event_type, detail, tracked, source=source
    ) as rec:
        # After recording() has taken the locks in the writers' order, so a frozen
        # product's stock records can neither be deleted nor race the switch.
        assert_products_usable(tracked, action="have its stock records deleted")
        _guard_stock_deletion(
            perform,
            product_ids=product_ids,
            packagings=packagings,
            loose_pools=loose_pools,
            extra_material_keys=extra_material_keys,
        )
        rec.actor = getattr(source, "deleted_by", None)


def _guard_stock_deletion(
    perform: Callable[[], None],
    *,
    product_ids: Iterable[int] = (),
    packagings: Iterable[ProductPackaging] = (),
    loose_pools: Iterable[tuple[Product, Decimal]] = (),
    extra_material_keys: Iterable[MaterialKey] = (),
) -> None:
    """Run ``perform`` -- soft-deleting a count line or an inward lot -- or refuse it.

    Every stock figure the deletion can move is read before and after it:
    available bags of ``packagings``, available loose packets of
    ``loose_pools``, raw kilograms of ``product_ids``, and every packing-material
    configuration those products have plus ``extra_material_keys``. The deletion is
    refused -- ``ValidationError``, which also rolls ``perform`` back -- when a
    figure ends up negative *and* lower than before. A figure that was already
    negative and does not move does not block it, the same rule the count
    writers apply (see ``_assert_material_available``).

    Deleting a count line can move more than its own pool: when the deleted
    row was the latest count date's last, an earlier day becomes "the latest
    count", and raw and packing material are re-derived from it.

    Locks are taken in the order the count writers take them -- raw pools, bag
    pools, loose pools, materials -- so a deletion and a count cannot deadlock.
    Must run inside ``transaction.atomic`` (``SoftDeletedModel`` provides it).
    """
    product_ids = sorted(set(product_ids))
    packagings = list(packagings)
    loose_pools = list(loose_pools)
    lock_raw_pools(product_ids)
    lock_bag_pools(packagings)
    lock_loose_pools(product.id for product, _ in loose_pools)
    watched = material_keys(product_ids) | set(extra_material_keys)
    _lock_materials(product_ids, {key[2] for key in watched})
    labels = _material_labels(watched)
    units = {
        material.id: material.unit_type
        for material in OtherMaterialType.all_objects.filter(
            id__in={key[2] for key in watched}
        )
    }

    def figures() -> dict[str, tuple[Decimal, str]]:
        """Each watched figure, by a label naming it, with its unit."""
        current: dict[str, tuple[Decimal, str]] = {}
        for packaging in packagings:
            current[f"'{packaging}'"] = (Decimal(available_bags(packaging)), "bags")
        for product, weight in loose_pools:
            current[f"'{product.name}' loose {weight}kg packets"] = (
                Decimal(available_loose_packets(product, weight)),
                "packets",
            )
        for product in Product.all_objects.filter(id__in=product_ids):
            current[f"raw material of '{product.name}'"] = (raw_available_kg(product), "kg")
        for key, available in other_material_available(watched).items():
            current[labels[key]] = (available, units[key[2]])
        return current

    before = figures()
    perform()
    after = figures()
    short = [
        f"{label} short by {-value} {unit}"
        for label, (value, unit) in after.items()
        if value < 0 and value < before[label][0]
    ]
    if short:
        raise ValidationError(f"This deletion would leave {'; '.join(short)}.")


def _assert_material_available(before: Mapping[MaterialKey, Decimal]) -> None:
    """Raise if the count just written took a packing material below zero.

    Only a write that *spends more* of a configuration's material and leaves it
    negative is refused. A configuration already short before this write --
    inward entries lagging behind the counts -- does not block a count that uses
    no more of it, so lowering a count is never refused. Same ``ValueError``
    convention as ``_assert_raw_available``: the whole write rolls back and the
    view answers 400.
    """
    after = other_material_available(before)
    short = [
        key
        for key, available in after.items()
        if available < 0 and available < before[key]
    ]
    if not short:
        return
    labels = _material_labels(short)
    units = {
        material.id: material.unit_type
        for material in OtherMaterialType.all_objects.filter(
            id__in={key[2] for key in short}
        )
    }
    details = "; ".join(
        f"{labels[key]} short by {-after[key]} {units[key[2]]}" for key in short
    )
    raise ValueError(f"Not enough packing material: {details}.")


# -- Shared -------------------------------------------------------------------


def order_bag_requirements(order: Order) -> dict[ProductPackaging, int]:
    """Bags each packaging must supply for ``order``.

    The single place order demand is computed, so the future custom-order flow
    lands here rather than being spread across the availability helpers.
    """
    requirements: dict[ProductPackaging, int] = {}
    for item in order.items.select_related("product_packaging"):
        packaging = item.product_packaging
        requirements[packaging] = requirements.get(packaging, 0) + item.quantity
    return requirements


def stock_position(snapshot_date: date | None = None) -> list[dict]:
    """The sealed-bag position for every counted packaging, ready for display.

    ``packets_on_hand`` is the **live** total still physically in the
    warehouse -- ``available + reserved`` -- not the raw count uploaded that
    day: a bag dispatched since the count was taken is gone, so it no longer
    counts as on hand even though the count itself hasn't been re-taken.
    ``packets_consumed`` is reported separately for visibility, but does not
    feed ``packets_on_hand``.

    Bags only -- loose stock is a different grain on a different lifecycle; see
    ``loose_stock_position``.
    """
    snapshot_date = snapshot_date or today()
    lines = []
    for line in snapshot_for(snapshot_date):
        packaging = line.product_packaging
        reserved = reserved_bags(packaging)
        available = available_bags(packaging, snapshot_date)
        lines.append(
            {
                "packaging": packaging,
                "product": packaging.product,
                "packets_on_hand": reserved + available,
                "packets_reserved": reserved,
                "packets_consumed": consumed_bags(packaging, snapshot_date),
                "packets_available": available,
            }
        )
    return lines


def snapshot_count_payload(snapshot: InventorySnapshot) -> dict:
    """What was counted on one line: the recorded figures, no derived position.

    Keyed by public ids only. The live reserved/consumed/available figures are
    left to :func:`snapshot_payload` -- they describe the stock *now*, not the
    day of the count, so a historical export must not carry them.
    """
    packaging = snapshot.product_packaging
    return {
        "public_id": snapshot.public_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "packaging": {
            "public_id": packaging.public_id,
            "product": {
                "public_id": packaging.product.public_id,
                "name": packaging.product.name,
            },
            "packet_weight": str(packaging.packet_weight),
            "packets": packaging.packets,
        },
        "bags": snapshot.bags,
        "total_packets": snapshot.total_packets,
        "total_weight": str(snapshot.total_weight),
    }


def snapshot_payload(snapshot: InventorySnapshot) -> dict:
    """Frontend-facing dict for one counted line, keyed by public ids only."""
    return {
        **snapshot_count_payload(snapshot),
        "packets_available": available_bags(
            snapshot.product_packaging, snapshot.snapshot_date
        ),
    }


def loose_stock_position(snapshot_date: date | None = None) -> list[dict]:
    """The loose position for every counted pool, ready for display.

    ``packets_on_hand`` is the live ``available + reserved`` total, not the
    raw counted figure -- see ``stock_position`` for why.
    """
    snapshot_date = loose_date(snapshot_date)
    lines = []
    for line in loose_lines(snapshot_date):
        product, weight = line.product, line.packet_weight
        reserved = reserved_loose_packets(product, weight)
        available = available_loose_packets(product, weight, snapshot_date)
        lines.append(
            {
                "product": product,
                "packet_weight": weight,
                "packets_on_hand": reserved + available,
                "packets_reserved": reserved,
                "packets_consumed": consumed_loose_packets(product, weight, snapshot_date),
                "packets_available": available,
            }
        )
    return lines


def loose_stock_count_payload(snapshot: LooseStockSnapshot) -> dict:
    """What was counted on one loose line: the recorded figures only.

    See :func:`snapshot_count_payload` for why the derived position is left out.
    """
    return {
        "public_id": snapshot.public_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "product": {
            "public_id": snapshot.product.public_id,
            "name": snapshot.product.name,
        },
        "packet_weight": str(snapshot.packet_weight),
        "packets": snapshot.packets,
        "total_weight": str(snapshot.total_weight),
    }


def loose_stock_payload(snapshot: LooseStockSnapshot) -> dict:
    """Frontend-facing dict for one loose line, keyed by public ids only."""
    product, weight = snapshot.product, snapshot.packet_weight
    return {
        **loose_stock_count_payload(snapshot),
        "reserved": reserved_loose_packets(product, weight),
        "consumed": consumed_loose_packets(product, weight, snapshot.snapshot_date),
        "available": available_loose_packets(product, weight, snapshot.snapshot_date),
    }
