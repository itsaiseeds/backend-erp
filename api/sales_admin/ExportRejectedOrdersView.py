"""Rejected-order export: ``GET /api/sales-admin/export/rejected-orders``.

``export/custom-orders`` over rejected orders booked in a date window.
"""

from __future__ import annotations

from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.CustomOrderOperations import custom_order_export_payload
from aggregator.models import CustomOrder, CustomOrderItem, kind_lookup
from api.export_serializers import ExportCustomOrderSerializer
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    export_response_serializer,
)

ExportRejectedOrdersResponseSerializer = export_response_serializer(
    "ExportRejectedOrdersResponseSerializer", ExportCustomOrderSerializer
)


class ExportRejectedOrdersView(AdminDateRangeExportView):
    """Export the rejected orders booked in a date window, with their items."""

    def export(self, window: DateWindow) -> list[dict]:
        orders = (
            window.created_between(CustomOrder.objects.filter(**kind_lookup("rejected")))
            .select_related(
                "client",
                "status",
                "delivery_address__city",
                "booked_for__address__pincode",
                "booked_for__address__city",
                "booked_for__address__state",
                "booked_for__address__country",
                "booked_for",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=CustomOrderItem.objects.select_related(
                        "product", "inward_raw_material__party"
                    ),
                )
            )
            .order_by("created_at", "id")
        )
        return [custom_order_export_payload(order) for order in orders]

    @extend_schema(
        operation_id="sales_admin_export_rejected_orders",
        summary="Export rejected orders (with items) booked in a date range",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportRejectedOrdersResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
