"""Stock-count export: ``GET /api/sales-admin/export/inventory-snapshots``.

Every live stock count whose ``snapshot_date`` falls inside the window, grouped
by that date::

    [{"snapshot_date": "2026-09-01",
      "bag_snapshots": [...],     # InventorySnapshot: sealed bags per packaging
      "loose_snapshots": [...]},  # LooseStockSnapshot: loose packets per pool
     ...]

Dates are ascending and only dates with at least one count appear. Rows carry
what was **counted** (:func:`~aggregator.InventoryOperations.snapshot_count_payload`,
:func:`~aggregator.InventoryOperations.loose_stock_count_payload`), not the live
reserved/available position, which describes today rather than the day of the
count. The window contract is in :mod:`api.export_views`.
"""

from __future__ import annotations

from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.InventoryOperations import (
    loose_stock_count_payload,
    snapshot_count_payload,
)
from aggregator.models import InventorySnapshot, LooseStockSnapshot
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    ExportResponseSerializer,
)


class ExportInventorySnapshotsView(AdminDateRangeExportView):
    """Export the bag and loose stock counts for a date window, grouped by date."""

    def export(self, window: DateWindow) -> list[dict]:
        days: dict[date, dict[str, list[dict]]] = {}

        def bucket(snapshot_date: date) -> dict[str, list[dict]]:
            return days.setdefault(
                snapshot_date, {"bag_snapshots": [], "loose_snapshots": []}
            )

        in_window = {"snapshot_date__range": (window.start_date, window.end_date)}
        for bag in InventorySnapshot.objects.filter(**in_window).select_related(
            "product_packaging__product"
        ):
            bucket(bag.snapshot_date)["bag_snapshots"].append(snapshot_count_payload(bag))
        for loose in LooseStockSnapshot.objects.filter(**in_window).select_related("product"):
            bucket(loose.snapshot_date)["loose_snapshots"].append(
                loose_stock_count_payload(loose)
            )

        return [{"snapshot_date": day.isoformat(), **days[day]} for day in sorted(days)]

    @extend_schema(
        operation_id="sales_admin_export_inventory_snapshots",
        summary="Export bag and loose stock counts for a date range, grouped by date",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
