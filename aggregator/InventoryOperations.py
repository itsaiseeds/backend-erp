"""Daily stock-count helpers for the ``aggregator`` sales domain.

The stock model is a **daily physical count**, not a running ledger. An admin
holding ``can_update_stock_count`` uploads what is on the floor; that count is
the day's opening balance. Only the latest ``snapshot_date`` is retained --
recording a count for a newer date hard-deletes every earlier row.

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
compulsory (``is_stock_count_complete`` gates order verification) and is
purged to its own latest date; the loose count is optional, written when it
changes, excluded from that gate, and purged to *its* own latest date. A bag
count for a new day must never delete a loose count that is still accurate.
Because a loose count may be days old and still correct, loose figures are read
at ``loose_date(...)`` -- the latest loose snapshot date -- rather than today.

Reserved and consumed quantities are **derived from ``Order.status``**, never
stored. That makes verification and dispatch inherently reversible (flip the
status back and the numbers correct themselves) and means outstanding
reservations survive the daily purge, which a stored counter would not.

Snapshots are exposed to the frontend by their ``public_id`` (``INV-…``);
payloads never include the internal primary key.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum

from common.models import indian_now

from .models import (
    CustomOrderItem,
    InventorySnapshot,
    LooseStockSnapshot,
    Order,
    OrderItem,
    Product,
    ProductPackaging,
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
    admin = getattr(actor, "admin_profile", None)
    if admin is None:
        raise PermissionDenied("Stock counts can only be recorded by a sales admin.")
    if not admin.can_update_stock_count:
        raise PermissionDenied(
            f"User '{actor}' is not allowed to update the stock count."
        )


# -- Writing the count --------------------------------------------------------


def _purge_older_than(snapshot_date: date) -> int:
    """Hard-delete every snapshot row for a date before ``snapshot_date``.

    Only the latest date is ever retained. This is a real SQL DELETE:
    ``SoftDeletedModel`` overrides the *instance* ``delete()`` only, so a
    queryset delete bypasses the soft-delete flags entirely. ``all_objects`` is
    used so already soft-deleted stragglers are removed too.
    """
    deleted, _ = InventorySnapshot.all_objects.filter(
        snapshot_date__lt=snapshot_date
    ).delete()
    return deleted


@transaction.atomic
def record_stock_count(
    *,
    product_packaging: ProductPackaging,
    bags: int,
    actor: User,
    snapshot_date: date | None = None,
) -> InventorySnapshot:
    """Record the count for a single packaging, then purge older days.

    Re-recording the same ``(snapshot_date, product_packaging)`` overwrites the
    earlier figures rather than adding a second row.
    """
    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()

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
    snapshot.is_deleted = False
    snapshot.deleted_at = None
    snapshot.deleted_by = None
    snapshot.full_clean()
    snapshot.save()

    _purge_older_than(snapshot_date)
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

    Every line is written and the older days are purged exactly once.
    """
    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()

    return [
        record_stock_count(
            product_packaging=product_packaging,
            bags=bags,
            actor=actor,
            snapshot_date=snapshot_date,
        )
        for product_packaging, bags in counts.items()
    ]


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


def _bag_demand(product_packaging: ProductPackaging, order_filter: dict) -> int:
    """Sum ``OrderItem.quantity`` for this packaging across matching orders."""
    total = OrderItem.objects.filter(
        product_packaging=product_packaging, **order_filter
    ).aggregate(total=Sum("quantity"))["total"]
    return total or 0


def reserved_bags(product_packaging: ProductPackaging) -> int:
    """Bags spoken for by verified orders that have not yet been dispatched."""
    return _bag_demand(
        product_packaging, {"order__status_id__in": RESERVING_STATUS_IDS}
    )


def consumed_bags(
    product_packaging: ProductPackaging, snapshot_date: date | None = None
) -> int:
    """Bags dispatched on or after ``snapshot_date``.

    Dispatches predating the count already left the warehouse before it was
    taken, so they are absent from the counted figure and must not be
    subtracted a second time.
    """
    snapshot_date = snapshot_date or today()
    base = {"order__status_id__in": CONSUMING_STATUS_IDS}
    return _bag_demand(
        product_packaging,
        {**base, "order__dispatch_details__dispatch_date__gte": snapshot_date},
    ) + _bag_demand(
        product_packaging,
        {**base, "order__private_dispatch_details__dispatch_date__gte": snapshot_date},
    )


def on_hand_bags(
    product_packaging: ProductPackaging, snapshot_date: date | None = None
) -> int:
    """Sealed bags counted for the day (0 when the packaging was not counted)."""
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


def _purge_loose_older_than(snapshot_date: date) -> int:
    """Hard-delete every loose row for a date before ``snapshot_date``.

    Scoped to ``LooseStockSnapshot`` alone: the bag purge and the loose purge
    never touch each other's table, which is what lets the loose count be
    optional and outlive any number of daily bag counts.
    """
    deleted, _ = LooseStockSnapshot.all_objects.filter(
        snapshot_date__lt=snapshot_date
    ).delete()
    return deleted


@transaction.atomic
def record_loose_stock(
    *,
    product: Product,
    packet_weight,
    packets: int,
    actor: User,
    snapshot_date: date | None = None,
) -> LooseStockSnapshot:
    """Record the loose count for one ``(product, packet_weight)``, then purge.

    Re-recording the same ``(snapshot_date, product, packet_weight)`` overwrites
    the earlier figure rather than adding a second row.
    """
    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()

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
    snapshot.is_deleted = False
    snapshot.deleted_at = None
    snapshot.deleted_by = None
    snapshot.full_clean()
    snapshot.save()

    _purge_loose_older_than(snapshot_date)
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
    written daily, or at all.
    """
    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()

    return [
        record_loose_stock(
            product=product,
            packet_weight=packet_weight,
            packets=packets,
            actor=actor,
            snapshot_date=snapshot_date,
        )
        for (product, packet_weight), packets in counts.items()
    ]


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


def _loose_demand(product: Product, packet_weight, order_filter: dict) -> int:
    """Sum ``CustomOrderItem.packets`` for this pool across matching custom orders."""
    total = CustomOrderItem.objects.filter(
        product=product, packet_weight=packet_weight, **order_filter
    ).aggregate(total=Sum("packets"))["total"]
    return total or 0


def reserved_loose_packets(product: Product, packet_weight) -> int:
    """Loose packets spoken for by verified custom orders not yet dispatched."""
    return _loose_demand(
        product, packet_weight, {"custom_order__status_id__in": RESERVING_STATUS_IDS}
    )


def consumed_loose_packets(
    product: Product, packet_weight, snapshot_date: date | None = None
) -> int:
    """Loose packets dispatched by custom orders on or after the count.

    Dispatches predating the count already left the warehouse before it was
    taken, so they are absent from the counted figure and must not be
    subtracted a second time.
    """
    snapshot_date = loose_date(snapshot_date)
    base = {"custom_order__status_id__in": CONSUMING_STATUS_IDS}
    return _loose_demand(
        product,
        packet_weight,
        {**base, "custom_order__dispatch_details__dispatch_date__gte": snapshot_date},
    ) + _loose_demand(
        product,
        packet_weight,
        {
            **base,
            "custom_order__private_dispatch_details__dispatch_date__gte": snapshot_date,
        },
    )


def on_hand_loose_packets(
    product: Product, packet_weight, snapshot_date: date | None = None
) -> int:
    """Loose packets counted for one ``(product, packet_weight)``.

    A single row lookup, not a sum across a product's packagings: the pool *is*
    the pair.
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

    Bags only -- loose stock is a different grain on a different lifecycle; see
    ``loose_stock_position``.
    """
    snapshot_date = snapshot_date or today()
    return [
        {
            "packaging": line.product_packaging,
            "product": line.product_packaging.product,
            "packets_on_hand": line.bags,
            "packets_reserved": reserved_bags(line.product_packaging),
            "packets_consumed": consumed_bags(line.product_packaging, snapshot_date),
            "packets_available": available_bags(line.product_packaging, snapshot_date),
        }
        for line in snapshot_for(snapshot_date)
    ]


def snapshot_payload(snapshot: InventorySnapshot) -> dict:
    """Frontend-facing dict for one counted line, keyed by public ids only."""
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
        "packets_available": available_bags(packaging, snapshot.snapshot_date),
    }


def loose_stock_position(snapshot_date: date | None = None) -> list[dict]:
    """The loose position for every counted pool, ready for display."""
    snapshot_date = loose_date(snapshot_date)
    return [
        {
            "product": line.product,
            "packet_weight": line.packet_weight,
            "packets_on_hand": line.packets,
            "packets_reserved": reserved_loose_packets(line.product, line.packet_weight),
            "packets_consumed": consumed_loose_packets(
                line.product, line.packet_weight, snapshot_date
            ),
            "packets_available": available_loose_packets(
                line.product, line.packet_weight, snapshot_date
            ),
        }
        for line in loose_lines(snapshot_date)
    ]


def loose_stock_payload(snapshot: LooseStockSnapshot) -> dict:
    """Frontend-facing dict for one loose line, keyed by public ids only."""
    product, weight = snapshot.product, snapshot.packet_weight
    return {
        "public_id": snapshot.public_id,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "product": {
            "public_id": product.public_id,
            "name": product.name,
        },
        "packet_weight": str(weight),
        "packets": snapshot.packets,
        "total_weight": str(snapshot.total_weight),
        "reserved": reserved_loose_packets(product, weight),
        "consumed": consumed_loose_packets(product, weight, snapshot.snapshot_date),
        "available": available_loose_packets(product, weight, snapshot.snapshot_date),
    }
