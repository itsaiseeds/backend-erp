"""Dispatch-receipt export: ``GET /api/sales-admin/export/dispatch-receipts``.

The challan of every order and custom order **booked** (``created_at``) inside
the window, oldest first. Which challans count is exactly the challan list's rule
(:data:`~api.sales_admin.GetDispatchChallansView.CHALLAN_Q`): the order is still
dispatched. An agency dispatch is included whether or not its LR number has been
recorded yet, so a receipt is exportable the moment the goods leave.

Each receipt is :func:`~aggregator.DispatchOperations.challan_entry_payload`
(a custom order's is the challan list's custom row, loose lines and
``order_type`` included): the order's public id, our consignor block, the
receiver as snapshotted at dispatch (company, GST, address with city, contact),
the journey, and every lot-numbered line with its quantity, price and total. ``city`` is
the order's own city (order -> delivery address -> city). The window contract
is in :mod:`api.export_views`.

"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.ClientOperations import order_city_payload
from aggregator.DispatchOperations import challan_entry_payload
from api.export_serializers import (
    ExportCustomDispatchReceiptSerializer,
    ExportDispatchReceiptSerializer,
)
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    export_response_serializer,
)

from .GetDispatchChallansView import challan_queryset

ExportDispatchReceiptsResponseSerializer = export_response_serializer(
    "ExportDispatchReceiptsResponseSerializer",
    ExportDispatchReceiptSerializer,
    ExportCustomDispatchReceiptSerializer,
)


class ExportDispatchReceiptsView(AdminDateRangeExportView):
    """Export the challans of orders and custom orders booked in a date window."""

    def export(self, window: DateWindow) -> list[dict]:
        entries = (
            window.created_between(challan_queryset(), field="order_created_at")
            .select_related(
                "order__delivery_address__city", "custom_order__delivery_address__city"
            )
            .order_by("order_created_at", "id")
        )
        return [
            {
                **challan_entry_payload(entry),
                "order_created_at": entry.source_order.created_at.isoformat(),
                "city": order_city_payload(entry.source_order),
            }
            for entry in entries
        ]

    @extend_schema(
        operation_id="sales_admin_export_dispatch_receipts",
        summary="Export dispatch receipts (challans) of orders booked in a date range",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportDispatchReceiptsResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
