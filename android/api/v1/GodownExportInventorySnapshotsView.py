"""Godown stock-count export: ``GET`` ``godown/export/inventory-snapshots``.

The Android counterpart of ``api.sales_admin.ExportInventorySnapshotsView``:
every live stock count -- bag (``InventorySnapshot``) and loose
(``LooseStockSnapshot``) -- interleaved into one flat, paginated list ordered by
``snapshot_date``, then kind, then id, built from the same DB-level UNION so
paging happens over both tables at once::

    {"total_count": 142, "total_pages": 5,
     "next_page_number": 2, "previous_page_number": null,
     "results": [
       {"kind": "bag", "public_id": "INV-...", "snapshot_date": "...", ...},
       {"kind": "loose", "public_id": "LS-...", "snapshot_date": "...", ...},
       ...
     ]}

Rows carry what was **counted** (``snapshot_count_payload`` /
``loose_stock_count_payload``), not the live reserved/available position, which
describes today rather than the day of the count. The ``start_date``/``end_date``
window is optional and uncapped -- give both to narrow the report, give neither
to page through the full history -- and a half-given window is a 400.
Godown-manager token only.
"""

from __future__ import annotations

from django.db.models import CharField, Value
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InventoryOperations import loose_stock_count_payload, snapshot_count_payload
from aggregator.models import InventorySnapshot, LooseStockSnapshot
from android.api.base import AndroidGodownBaseView
from api.sales_admin.ExportInventorySnapshotsView import (
    ExportInventorySnapshotsPageSerializer,
    _OptionalDateWindowSerializer,
)
from common.views.paginated_date_range import (
    StandardPageNumberPagination,
    pagination_query_parameters,
)


class GodownExportInventorySnapshotsView(AndroidGodownBaseView):
    """Export bag and loose stock counts, interleaved and paginated."""

    pagination_class = StandardPageNumberPagination

    @extend_schema(
        operation_id="android_api_v1_godown_export_inventory_snapshots",
        summary="Export bag and loose stock counts, interleaved and paginated",
        parameters=[
            *pagination_query_parameters(),
            OpenApiParameter(
                "start_date",
                OpenApiTypes.DATE,
                required=False,
                description=(
                    "First day of the window (inclusive, IST). Optional -- "
                    "give together with end_date, or omit both for the full "
                    "history."
                ),
            ),
            OpenApiParameter(
                "end_date",
                OpenApiTypes.DATE,
                required=False,
                description=(
                    "Last day of the window (inclusive, IST). Optional -- "
                    "give together with start_date, or omit both for the "
                    "full history."
                ),
            ),
        ],
        responses={200: ExportInventorySnapshotsPageSerializer},
    )
    def get(self, request: Request) -> Response:
        window = _OptionalDateWindowSerializer(data=request.query_params)
        window.is_valid(raise_exception=True)
        start_date = window.validated_data.get("start_date")
        end_date = window.validated_data.get("end_date")

        bag_qs = InventorySnapshot.objects.all()
        loose_qs = LooseStockSnapshot.objects.all()
        if start_date and end_date:
            bag_qs = bag_qs.filter(snapshot_date__range=(start_date, end_date))
            loose_qs = loose_qs.filter(snapshot_date__range=(start_date, end_date))

        # A DB-level UNION of just the sort/identity columns, so paging (LIMIT
        # / OFFSET) happens in the database over both tables at once. Only
        # count(), order_by() and slicing are usable on a combined queryset --
        # everything else (further filter()/annotate()) must happen before the
        # union, which is why the window is applied to each side above.
        bag_keys = bag_qs.annotate(kind=Value("bag", output_field=CharField())).values(
            "id", "kind", "snapshot_date"
        )
        loose_keys = loose_qs.annotate(kind=Value("loose", output_field=CharField())).values(
            "id", "kind", "snapshot_date"
        )
        combined = bag_keys.union(loose_keys, all=True).order_by("snapshot_date", "kind", "id")

        paginator = self.pagination_class()
        page_keys = paginator.paginate_queryset(combined, request, view=self) or []

        # The union only carried ids; fetch the real rows for just this page,
        # one bulk query per kind, then rebuild the page in its original order.
        bag_ids = [row["id"] for row in page_keys if row["kind"] == "bag"]
        loose_ids = [row["id"] for row in page_keys if row["kind"] == "loose"]
        bags_by_id = {
            snap.id: snap
            for snap in InventorySnapshot.objects.filter(id__in=bag_ids).select_related(
                "product_packaging__product"
            )
        }
        loose_by_id = {
            snap.id: snap
            for snap in LooseStockSnapshot.objects.filter(id__in=loose_ids).select_related(
                "product"
            )
        }

        results = [
            {"kind": "bag", **snapshot_count_payload(bags_by_id[row["id"]])}
            if row["kind"] == "bag"
            else {"kind": "loose", **loose_stock_count_payload(loose_by_id[row["id"]])}
            for row in page_keys
        ]
        return paginator.get_paginated_response(results)
