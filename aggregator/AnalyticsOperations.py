"""Read-time analytics for a sales person's own book of business.

Everything is derived on the fly from ``Order`` and ``Client`` rows the user
created, inside a ``created_at`` window; nothing is stored. Counts are always
returned for **every** status of the domain (zero when none), so a client can
render a fixed set of buckets without guessing which are missing.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from django.db.models import Count

from .models import Client, Order
from .models.Status import StatusIds

ORDER_STATUS_CODES = [status.name for status in StatusIds.order_statuses()]
CLIENT_STATUS_CODES = [status.name for status in StatusIds.client_statuses()]


def _zero_filled(codes: Iterable[str], counts: dict[str, int]) -> dict[str, int]:
    return {code: counts.get(code, 0) for code in codes}


def sales_person_analytics(user, start: datetime, end: datetime) -> dict:
    """Order, client and per-client order counts by status for ``user``.

    The window is inclusive on both ends and applies to each row's own
    ``created_at``: orders booked in the window, clients created in the window.
    ``client_orders`` lists every client the user booked at least one order for
    in the window -- including a client created before it -- busiest first.
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

    per_client: dict[int, dict] = {}
    rows = orders.values("client_id", "client__public_id", "client__company_name", "status__code")
    for row in rows.annotate(count=Count("pk")):
        entry = per_client.setdefault(
            row["client_id"],
            {
                "client": {
                    "public_id": row["client__public_id"],
                    "company_name": row["client__company_name"],
                },
                "counts": {},
            },
        )
        entry["counts"][row["status__code"]] = row["count"]

    client_orders = [
        {
            "client": entry["client"],
            "total": sum(entry["counts"].values()),
            "by_status": _zero_filled(ORDER_STATUS_CODES, entry["counts"]),
        }
        for entry in per_client.values()
    ]
    client_orders.sort(key=lambda row: (-row["total"], row["client"]["company_name"].lower()))

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
        "client_orders": client_orders,
    }
