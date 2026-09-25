"""Stock-count export: ``GET /api/sales-admin/export/inventory-snapshots``.

Every live stock count -- bag (``InventorySnapshot``) and loose
(``LooseStockSnapshot``) -- interleaved into one flat, paginated list ordered
by ``snapshot_date``, then kind, then id::

    {"total_count": 142, "total_pages": 5,
     "next_page_number": 2, "previous_page_number": null,
     "results": [
       {"kind": "bag", "public_id": "INV-...", "snapshot_date": "...", ...},
       {"kind": "loose", "public_id": "LS-...", "snapshot_date": "...", ...},
       ...
     ]}

Unlike the other ``export/...`` endpoints (see ``api.export_views``), a stock
count spans the entire life of the business rather than a bounded period, so
this one is **paginated** rather than returned whole, and its
``start_date``/``end_date`` window is **optional and uncapped** -- give both
to narrow the report to a range, give neither to page through the full
history.

Rows carry what was **counted**
(:func:`~aggregator.InventoryOperations.snapshot_count_payload`,
:func:`~aggregator.InventoryOperations.loose_stock_count_payload`), not the
live reserved/available position, which describes today rather than the day
of the count.
"""

from __future__ import annotations

from django.db.models import CharField, Value
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_field,
)
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.InventoryOperations import (
    loose_stock_count_payload,
    snapshot_count_payload,
)
from aggregator.models import InventorySnapshot, LooseStockSnapshot
from api.admin import AdminApiView
from api.export_serializers import (
    ExportBagSnapshotSerializer,
    ExportLooseSnapshotSerializer,
)
from common.views.paginated_date_range import StandardPageNumberPagination


class _OptionalDateWindowSerializer(serializers.Serializer):
    """``start_date``/``end_date`` are optional here, but come as a pair."""

    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if bool(start) != bool(end):
            raise serializers.ValidationError(
                "Provide both start_date and end_date, or neither."
            )
        if start and end and start > end:
            raise serializers.ValidationError(
                "start_date must be less than or equal to end_date."
            )
        return attrs


class ExportInventorySnapshotsPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = serializers.SerializerMethodField()

    @extend_schema_field(
        # ``resource_type_field_name=None``: each row already carries its own
        # ``kind`` literal (see ExportBagSnapshotSerializer /
        # ExportLooseSnapshotSerializer), but drf-spectacular's discriminator
        # mapping calls ``field.to_representation(None)`` to build it, which a
        # plain ChoiceField answers with ``None`` -- the same reason
        # StockView's polymorphic response disables it too.
        PolymorphicProxySerializer(
            component_name="ExportInventorySnapshotRow",
            serializers=[ExportBagSnapshotSerializer, ExportLooseSnapshotSerializer],
            resource_type_field_name=None,
            many=True,
        )
    )
    def get_results(self, obj):
        return obj["results"]


class ExportInventorySnapshotsView(AdminApiView):
    """Export bag and loose stock counts, interleaved and paginated."""

    admin_required = True
    pagination_class = StandardPageNumberPagination

    @extend_schema(
        operation_id="sales_admin_export_inventory_snapshots",
        summary="Export bag and loose stock counts, interleaved and paginated",
        parameters=[
            OpenApiParameter(
                "page", OpenApiTypes.INT, description="1-based page number."
            ),
            OpenApiParameter(
                "page_size",
                OpenApiTypes.INT,
                description="Rows per page (default 10, max 30).",
            ),
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
    def get(self, request: Request, *args, **kwargs):
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
        bag_keys = bag_qs.annotate(
            kind=Value("bag", output_field=CharField())
        ).values("id", "kind", "snapshot_date")
        loose_keys = loose_qs.annotate(
            kind=Value("loose", output_field=CharField())
        ).values("id", "kind", "snapshot_date")
        combined = bag_keys.union(loose_keys, all=True).order_by(
            "snapshot_date", "kind", "id"
        )

        paginator = self.pagination_class()
        page_keys = paginator.paginate_queryset(combined, request, view=self)

        # The union only carried ids; fetch the real rows for just this page,
        # one bulk query per kind, then rebuild the page in its original order.
        bag_ids = [row["id"] for row in page_keys if row["kind"] == "bag"]
        loose_ids = [row["id"] for row in page_keys if row["kind"] == "loose"]
        bags_by_id = {
            snap.id: snap
            for snap in InventorySnapshot.objects.filter(
                id__in=bag_ids
            ).select_related("product_packaging__product")
        }
        loose_by_id = {
            snap.id: snap
            for snap in LooseStockSnapshot.objects.filter(
                id__in=loose_ids
            ).select_related("product")
        }

        results = [
            {"kind": "bag", **snapshot_count_payload(bags_by_id[row["id"]])}
            if row["kind"] == "bag"
            else {"kind": "loose", **loose_stock_count_payload(loose_by_id[row["id"]])}
            for row in page_keys
        ]
        return paginator.get_paginated_response(results)
