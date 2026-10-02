"""Daily stock-count helpers for the ``aggregator`` sales domain.

The stock model is a **daily physical count**, not a running ledger. An admin
holding ``can_update_stock_count`` uploads what is on the floor; that count is
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
from django.db import transaction
from django.db.models import Q, Sum

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
    Product,
    ProductPackaging,
    RawMaterialWaste,
    StatusIds,
)

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

    ``Admin.can_update_stock_count`` gates exactly this and nothing else -- in
    particular it does **not** gate order verification.
    """
    if actor is None:
        raise PermissionDenied("A user must be provided to record a stock count.")
    if getattr(actor, "is_superuser", False):
        return
    admin = getattr(actor, "live_admin_profile", None)
    if admin is None:
        raise PermissionDenied("Stock counts can only be recorded by a sales admin.")
    if not admin.can_update_stock_count:
        raise PermissionDenied(
            f"User '{actor}' is not allowed to update the stock count."
        )


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
    _assert_can_update_stock_count(actor)
    lock_raw_pools([product_packaging.product_id])
    materials_before = _material_guard([product_packaging.product_id])
    snapshot = _write_stock_count(
        product_packaging=product_packaging,
        bags=bags,
        actor=actor,
        snapshot_date=snapshot_date or today(),
    )
    _assert_raw_available([product_packaging.product_id])
    _assert_material_available(materials_before)
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
    snapshot = InventorySnapshot.all_objects.filter(
        snapshot_date=snapshot_date, product_packaging=product_packaging
    ).first()
    if snapshot is None:
        snapshot = InventorySnapshot(
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
    return snapshot


@transaction.atomic
def record_stock_counts(
    *,
    counts: Mapping[ProductPackaging, int],
    actor: User,
    snapshot_date: date | None = None,
) -> list[InventorySnapshot]:
    """Upload a whole day's bag count in one transaction.

    ``counts`` maps a ``ProductPackaging`` to its bag count::

        record_stock_counts(counts={pack_a: 400, pack_b: 10}, actor=admin)

    Loose stock is *not* recorded here -- it is a separate, optional count; see
    ``record_loose_stocks``.

    Every line is written; earlier days' counts are kept as history.

    The raw-material check runs once, after every line is written, so one
    upload may raise one packaging of a product and lower another: only the
    net kilograms per product must fit its raw pool. The packing-material
    check works the same way, per material type. Any shortfall rolls the
    whole upload back.
    """
    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()
    product_ids = {packaging.product_id for packaging in counts}
    lock_raw_pools(product_ids)
    # All up front and in pk order; _write_stock_count re-takes each as a no-op.
    lock_bag_pools(counts)
    materials_before = _material_guard(product_ids)

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
    _assert_material_available(materials_before)
    return snapshots


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
    """Active packagings with no counted line for ``snapshot_date``."""
    counted = snapshot_for(snapshot_date).values_list("product_packaging_id", flat=True)
    return ProductPackaging.objects.exclude(id__in=counted)


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
    _assert_can_update_stock_count(actor)
    lock_raw_pools([product.id])
    materials_before = _material_guard([product.id])
    snapshot = _write_loose_stock(
        product=product,
        packet_weight=packet_weight,
        packets=packets,
        actor=actor,
        snapshot_date=snapshot_date or today(),
    )
    _assert_raw_available([product.id])
    _assert_material_available(materials_before)
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
    snapshot = LooseStockSnapshot.all_objects.filter(
        snapshot_date=snapshot_date, product=product, packet_weight=packet_weight
    ).first()
    if snapshot is None:
        snapshot = LooseStockSnapshot(
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
    return snapshot


@transaction.atomic
def record_loose_stocks(
    *,
    counts: Mapping[tuple[Product, Decimal], int],
    actor: User,
    snapshot_date: date | None = None,
) -> list[LooseStockSnapshot]:
    """Upload a whole loose count in one transaction.

    ``counts`` maps a ``(product, packet_weight)`` pair to its packet count::

        record_loose_stocks(counts={(product, Decimal("1.000")): 12}, actor=admin)

    Unlike the bag count this is **optional** -- nothing requires it to be
    written daily, or at all. Like the bag count, the net kilograms per product
    must fit its raw pool, and the net units per packing material its
    material pool, or the whole upload rolls back.
    """
    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()
    product_ids = {product.id for product, _ in counts}
    lock_raw_pools(product_ids)
    # All up front and in pk order; _write_loose_stock re-takes each as a no-op.
    lock_loose_pools(product_ids)
    materials_before = _material_guard(product_ids)

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
    _assert_material_available(materials_before)
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
    ``_assert_raw_available``.
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
    lock_raw_pools([product.id])
    waste = RawMaterialWaste.objects.create(
        product=product,
        quantity_kg=quantity_kg,
        reason=reason.strip(),
        created_by=actor,
    )
    _assert_raw_available([product.id])
    return waste


# -- Packing (other) material backing -----------------------------------------
#
# Every packet also uses packing material -- leaflets, covers -- per the
# product's ``OtherMaterialRecipe`` for its packet weight: ``recipe.quantity``
# units of the material type per packet. The pool is the **material type**:
# inward lots are booked against a recipe but any recipe of a type draws on
# the same stock. Spent material is derived exactly like raw kilograms, from
# the packets currently packed (latest bag and loose counts, plus what was
# dispatched before them), valued at each product's *current* recipe.


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


def other_material_inward(
    material_type_ids: Iterable[int] | None = None, as_of: date | None = None
) -> dict[int, Decimal]:
    """Units received per material type, over lots with a reached effective date.

    Lots booked against a since-replaced recipe still count: the stock is the
    material type's, whichever recipe version brought it in.
    """
    as_of = as_of or today()
    query = InwardOtherMaterial.objects.filter(
        effective_date__isnull=False, effective_date__lte=as_of
    )
    if material_type_ids is not None:
        query = query.filter(recipe__material_type_id__in=list(material_type_ids))
    rows = query.values("recipe__material_type_id").annotate(total=Sum("quantity"))
    return {row["recipe__material_type_id"]: row["total"] for row in rows}


def other_material_used(
    material_type_ids: Iterable[int] | None = None,
) -> dict[int, Decimal]:
    """Units per material type spent on the packets currently packed.

    Each live recipe charges ``quantity`` per packed packet of its product at
    its packet weight; packets of a weight with no recipe for the type use none.
    """
    recipes = OtherMaterialRecipe.objects.all()
    if material_type_ids is not None:
        recipes = recipes.filter(material_type_id__in=list(material_type_ids))
    used: dict[int, Decimal] = {}
    packed_by_product: dict[int, dict[Decimal, int]] = {}
    for recipe in recipes.select_related("product"):
        if recipe.product_id not in packed_by_product:
            packed_by_product[recipe.product_id] = packed_packets(recipe.product)
        packets = packed_by_product[recipe.product_id].get(recipe.packet_weight, 0)
        used[recipe.material_type_id] = (
            used.get(recipe.material_type_id, Decimal("0")) + recipe.quantity * packets
        )
    return used


def other_material_available(material_type_ids: Iterable[int]) -> dict[int, Decimal]:
    """``inward - used`` for each of ``material_type_ids``."""
    material_type_ids = list(material_type_ids)
    inward = other_material_inward(material_type_ids)
    used = other_material_used(material_type_ids)
    return {
        material_type_id: inward.get(material_type_id, Decimal("0"))
        - used.get(material_type_id, Decimal("0"))
        for material_type_id in material_type_ids
    }


def _lock_materials(product_ids, material_type_ids: Iterable[int] = ()) -> list[int]:
    """Lock the material types ``product_ids``' recipes use, plus ``material_type_ids``.

    Rows are locked in pk order, so two writers sharing a material cannot both
    spend its last units. Returns the locked ids.
    """
    locked = sorted(
        set(
            OtherMaterialRecipe.objects.filter(product_id__in=product_ids).values_list(
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


def _material_guard(product_ids) -> dict[int, Decimal]:
    """Lock the packing materials ``product_ids`` use; return their availability.

    Called before a count write, inside its transaction. The returned figures
    are what :func:`_assert_material_available` compares the write against.
    """
    return other_material_available(_lock_materials(product_ids))


def guard_stock_deletion(
    perform: Callable[[], None],
    *,
    product_ids: Iterable[int] = (),
    packagings: Iterable[ProductPackaging] = (),
    loose_pools: Iterable[tuple[Product, Decimal]] = (),
    material_type_ids: Iterable[int] = (),
) -> None:
    """Run ``perform`` -- soft-deleting a count line or an inward lot -- or refuse it.

    Every stock figure the deletion can move is read before and after it:
    available bags of ``packagings``, available loose packets of
    ``loose_pools``, raw kilograms of ``product_ids``, and every packing
    material those products use plus ``material_type_ids``. The deletion is
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
    material_ids = _lock_materials(product_ids, material_type_ids)
    materials = {
        material.id: material
        for material in OtherMaterialType.all_objects.filter(id__in=material_ids)
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
        for material_id, available in other_material_available(material_ids).items():
            material = materials[material_id]
            current[f"'{material.name}'"] = (available, material.unit_type)
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


def _assert_material_available(before: Mapping[int, Decimal]) -> None:
    """Raise if the count just written took a packing material below zero.

    Only a write that *spends more* of a material and leaves it negative is
    refused. A material already short before this write -- inward entries
    lagging behind the counts -- does not block a count that uses no more of
    it, so lowering a count is never refused. Same ``ValueError`` convention
    as ``_assert_raw_available``: the whole write rolls back and the view
    answers 400.
    """
    after = other_material_available(before)
    short = [
        material_type_id
        for material_type_id, available in after.items()
        if available < 0 and available < before[material_type_id]
    ]
    if not short:
        return
    names = {
        material.id: material
        for material in OtherMaterialType.all_objects.filter(id__in=short)
    }
    details = "; ".join(
        f"'{names[material_type_id].name}' short by "
        f"{-after[material_type_id]} {names[material_type_id].unit_type}"
        for material_type_id in short
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
