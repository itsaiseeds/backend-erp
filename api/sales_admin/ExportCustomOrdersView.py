"""Custom-order export: ``GET /api/sales-admin/export/custom-orders``.

Every live custom order **booked** (``created_at``) inside the window, oldest
first, each with its loose-packet lines nested -- the product, the packet
weight, the negotiated per-packet price, the packet count and the line total.
The client is named with its delivery city. See :mod:`api.export_views` for the
window contract.
"""

from __future__ import annotations

from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.CustomOrderOperations import custom_order_export_payload
from aggregator.models import CustomOrder, CustomOrderItem
from api.export_serializers import ExportCustomOrderSerializer
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    export_response_serializer,
)

ExportCustomOrdersResponseSerializer = export_response_serializer(
    "ExportCustomOrdersResponseSerializer", ExportCustomOrderSerializer
)


class ExportCustomOrdersView(AdminDateRangeExportView):
    """Export the custom orders booked in a date window, with their items."""

    def export(self, window: DateWindow) -> list[dict]:
        orders = (
            window.created_between(CustomOrder.objects.all())
            .select_related("client", "status", "delivery_address__city")
            .prefetch_related(
                Prefetch("items", queryset=CustomOrderItem.objects.select_related("product"))
            )
            .order_by("created_at", "id")
        )
        return [custom_order_export_payload(order) for order in orders]

    @extend_schema(
        operation_id="sales_admin_export_custom_orders",
        summary="Export custom orders (with items) booked in a date range",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportCustomOrdersResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
