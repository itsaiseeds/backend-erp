"""Daily stock-count helpers for the ``aggregator`` sales domain.

The stock model is a **daily physical count**, not a running ledger. An admin
holding ``can_update_stock_count`` uploads what is on the floor; that count is
the day's opening balance. Only the latest ``snapshot_date`` is retained --
recording a count for a newer date hard-deletes every earlier row.

Stock lives in two pools that never mix:

* ``bags``    - sealed whole packagings, consumed by normal ``OrderItem``
  lines. Counted in bags, the same unit as ``OrderItem.quantity``.
* ``loose_packets`` - unpacked single packets, reserved for the future custom-order
  flow. Counted in packets. A packaged order may never be filled from loose stock,
  and a custom order may never break open a bag.

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
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum

from common.models import indian_now

from .models import (
    CustomOrderItem,
    InventorySnapshot,
    OrderItem,
    Product,
    ProductPackaging,
    StatusIds,
)

# Orders holding sealed bags: verified, not yet gone.
RESERVING_STATUS_IDS = (StatusIds.CONFIRMED,)
# Orders whose bags have physically left the warehouse.
CONSUMING_STATUS_IDS = (StatusIds.DISPATCHED, StatusIds.DELIVERED)


def today() -> date:
    """Today in the project's timezone (Asia/Kolkata)."""
    return indian_now().date()


def _assert_can_update_stock_count(actor: Any) -> None:
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
    actor: Any,
    loose_packets: int = 0,
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
    snapshot.loose_packets = loose_packets
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
    counts: Mapping[Any, Any],
    actor: Any,
    snapshot_date: date | None = None,
) -> list[InventorySnapshot]:
    """Upload a whole day's count in one transaction.

    ``counts`` maps a ``ProductPackaging`` to either a bare bag count or a
    ``{"bags": n, "loose_packets": m}`` mapping::

        record_stock_counts(counts={pack_a: 400, pack_b: {"bags": 10, "loose_packets": 5}},
                            actor=admin)

    Every line is written and the older days are purged exactly once.
    """
    _assert_can_update_stock_count(actor)
    snapshot_date = snapshot_date or today()

    snapshots = []
    for product_packaging, value in counts.items():
        if isinstance(value, Mapping):
            bags = value.get("bags", 0)
            loose_packets = value.get("loose_packets", 0)
        else:
            bags, loose_packets = value, 0
        snapshots.append(
            record_stock_count(
                product_packaging=product_packaging,
                bags=bags,
                loose_packets=loose_packets,
                actor=actor,
                snapshot_date=snapshot_date,
            )
        )
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


# -- Deriving position: loose packets (per PRODUCT) ------------------------------
#
# The loose pool is consumed only by custom orders (``CustomOrderItem`` lines),
# which deal in a raw ``Product`` and a packet count -- they never name a
# packaging. So the loose pool is tracked **per product**, not per packaging:
# on-hand loose for a product is the sum of ``loose_packets`` across that product's
# counted packagings. The reserve/consume logic mirrors the bag pool exactly
# -- keyed off the custom order's status and dispatch dates -- so it is
# reversible for free and a dispatch predating the count is never subtracted
# twice.


def _loose_demand(product: Product, order_filter: dict) -> int:
    """Sum ``CustomOrderItem.packets`` for this product across matching custom orders."""
    total = CustomOrderItem.objects.filter(
        product=product, **order_filter
    ).aggregate(total=Sum("packets"))["total"]
    return total or 0


def reserved_loose_packets(product: Product) -> int:
    """Loose packets spoken for by verified custom orders not yet dispatched."""
    return _loose_demand(
        product, {"custom_order__status_id__in": RESERVING_STATUS_IDS}
    )


def consumed_loose_packets(product: Product, snapshot_date: date | None = None) -> int:
    """Loose packets dispatched by custom orders on or after ``snapshot_date``.

    Dispatches predating the count already left the warehouse before it was
    taken, so they are absent from the counted figure and must not be
    subtracted a second time.
    """
    snapshot_date = snapshot_date or today()
    base = {"custom_order__status_id__in": CONSUMING_STATUS_IDS}
    return _loose_demand(
        product,
        {**base, "custom_order__dispatch_details__dispatch_date__gte": snapshot_date},
    ) + _loose_demand(
        product,
        {
            **base,
            "custom_order__private_dispatch_details__dispatch_date__gte": snapshot_date,
        },
    )


def on_hand_loose_packets(product: Product, snapshot_date: date | None = None) -> int:
    """Loose packets counted for a product, summed across its counted packagings."""
    total = InventorySnapshot.objects.filter(
        snapshot_date=snapshot_date or today(),
        product_packaging__product=product,
    ).aggregate(total=Sum("loose_packets"))["total"]
    return total or 0


def available_loose_packets(product: Product, snapshot_date: date | None = None) -> int:
    """Loose packets of a product still sellable. Never touched by packaged orders."""
    snapshot_date = snapshot_date or today()
    return (
        on_hand_loose_packets(product, snapshot_date)
        - reserved_loose_packets(product)
        - consumed_loose_packets(product, snapshot_date)
    )


# -- Shared -------------------------------------------------------------------


def order_bag_requirements(order: Any) -> dict[ProductPackaging, int]:
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
    """Both pools for every counted packaging, ready for display.

    Bag figures are per packaging (a normal order names a packaging); loose
    figures are per **product** (a custom order names a raw product), so the
    loose numbers repeat across every counted packaging of the same product.
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
            "loose_packets_on_hand": line.loose_packets,
            "product_loose_packets_reserved": reserved_loose_packets(
                line.product_packaging.product
            ),
            "product_loose_packets_consumed": consumed_loose_packets(
                line.product_packaging.product, snapshot_date
            ),
            "product_loose_packets_available": available_loose_packets(
                line.product_packaging.product, snapshot_date
            ),
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
        "loose_packets": snapshot.loose_packets,
        "total_packets": snapshot.total_packets,
        "total_weight": str(snapshot.total_weight),
        "packets_available": available_bags(packaging, snapshot.snapshot_date),
        # Loose availability is a per-product figure (custom orders name a raw
        # product, not a packaging).
        "product_loose_packets_available": available_loose_packets(
            packaging.product, snapshot.snapshot_date
        ),
    }
