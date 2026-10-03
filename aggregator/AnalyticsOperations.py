"""Read-time analytics for a sales person's own book of business.

Everything is derived on the fly from ``Order``, ``OrderItem`` and ``Client``
rows the user created, inside a ``created_at`` window; nothing is stored. Counts
are always returned for **every** status of the domain (zero when none), so a
client can render a fixed set of buckets without guessing which are missing.

The headline numbers stay counts -- how many orders, how many clients. The
weight booked is reported separately, per product: each product row splits its
kilograms across the order statuses, so ``BOOKED`` is the weight still
un-verified, ``CONFIRMED`` the weight a sales admin approved, and so on.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum

from .models import Client, Order, OrderItem
from .models.Status import StatusIds

ORDER_STATUS_CODES = [status.name for status in StatusIds.order_statuses()]
CLIENT_STATUS_CODES = [status.name for status in StatusIds.client_statuses()]

NO_KG = Decimal("0.000")

# Kilograms on one order line: ``quantity`` bags of ``packets`` packets at
# ``packet_weight`` kg each. Every factor resolves to exactly one row on this
# query -- ``quantity`` is the base table's own column and the other two come
# through forward FKs -- so summing the product cannot double-count a line.
# Mirrors ``Order.total_packets``' arithmetic, and reads the packaging live:
# a lookup across a relation does not pick up any soft-delete manager either.
_LINE_KG = F("quantity") * F("product_packaging__packet_weight") * F("product_packaging__packets")
# Pinned rather than inferred: an integer product would have the decimals
# rounded away to whole packets, and three is ``packet_weight``'s own precision.
_KG = DecimalField(max_digits=14, decimal_places=3)


def _zero_filled(codes: Iterable[str], counts: dict[str, int]) -> dict[str, int]:
    return {code: counts.get(code, 0) for code in codes}


def _zero_filled_kg(codes: Iterable[str], weights: dict[str, Decimal]) -> dict[str, str]:
    """``codes`` mapped to their kilograms, every bucket present.

    Rendered as a string with three decimals so a decimal weight never reaches
    JSON as a lossy float -- the same call ``ProductOperations`` uses for money.
    """
    return {code: str(weights.get(code, NO_KG)) for code in codes}


def sales_person_analytics(user, start: datetime, end: datetime) -> dict:
    """Order and client counts by status, plus the kg booked, per product.

    The window is inclusive on both ends and applies to each row's own
    ``created_at``: orders booked in the window, clients created in the window.
    Both count buckets are zero-filled over every status code, so a client can
    render a fixed set of buckets without guessing which are missing.

    ``products`` lists every product the user booked any weight for in the
    window -- heaviest first -- each with its kilograms split by the order's
    current status. Verifying an order therefore moves its kg from ``BOOKED``
    to ``CONFIRMED`` without ever leaving the product's ``total_kg``.
    """
    orders = Order.objects.filter(created_by=user, created_at__gte=start, created_at__lte=end)
    clients = Client.objects.filter(created_by=user, created_at__gte=start, created_at__lte=end)

    order_counts = {
        row["status__code"]: row["count"]
        for row in orders.values("status__code").annotate(count=Count("pk"))
    }
    client_counts = {
        row["status__code"]: row["count"]
        for row in clients.values("status__code").annotate(count=Count("pk"))
    }

    # Kilograms per (product, status), weighted over the order's *lines* rather
    # than the order itself: joining ``items`` onto the count query above would
    # multiply each order by its line count. ``order__in=orders`` keeps the same
    # caller/window (and the same soft-delete filter) the counts came from, so
    # the two can never disagree; ``OrderItem.objects`` drops deleted lines, the
    # way ``Order.total_packets`` does.
    per_product: dict[int, dict] = {}
    rows = (
        OrderItem.objects.filter(order__in=orders)
        .values(
            "product_packaging__product_id",
            "product_packaging__product__public_id",
            "product_packaging__product__name",
            "order__status__code",
        )
        .annotate(kg=Sum(_LINE_KG, output_field=_KG))
    )
    for row in rows:
        code = row["order__status__code"]
        entry = per_product.setdefault(
            row["product_packaging__product_id"],
            {
                "product": {
                    "public_id": row["product_packaging__product__public_id"],
                    "name": row["product_packaging__product__name"],
                },
                "kg": {},
            },
        )
        entry["kg"][code] = entry["kg"].get(code, NO_KG) + row["kg"]

    products = [
        {
            "product": entry["product"],
            "total_kg": str(sum(entry["kg"].values(), NO_KG)),
            "kg_by_status": _zero_filled_kg(ORDER_STATUS_CODES, entry["kg"]),
        }
        # Heaviest first; the name only ever breaks a tie.
        for entry in sorted(
            per_product.values(),
            key=lambda entry: (
                -sum(entry["kg"].values(), NO_KG),
                entry["product"]["name"].lower(),
            ),
        )
    ]

    return {
        "start_date_time": start,
        "end_date_time": end,
        "orders": {
            "total": sum(order_counts.values()),
            "by_status": _zero_filled(ORDER_STATUS_CODES, order_counts),
        },
        "clients": {
            "total": sum(client_counts.values()),
            "by_status": _zero_filled(CLIENT_STATUS_CODES, client_counts),
        },
        "products": products,
    }
