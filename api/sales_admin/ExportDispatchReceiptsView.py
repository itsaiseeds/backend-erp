"""Dispatch-receipt export: ``GET /api/sales-admin/export/dispatch-receipts``.

The complete challan of every order **booked** (``created_at``) inside the
window, oldest order first. "Complete" is exactly the challan list's rule
(:data:`~api.sales_admin.GetDispatchChallansView.CHALLAN_Q`): the order is still
dispatched, and an agency dispatch has its LR number recorded.

Each receipt is :func:`~aggregator.DispatchOperations.dispatch_challan_payload`:
the order's public id, our consignor block, the receiver as snapshotted at
dispatch (company, GST, address with city, contact), the journey, and every
lot-numbered line with its packaging, quantity, price and total. ``city`` is
the order's own city (order -> delivery address -> city). The window contract
is in :mod:`api.export_views`.

Only normal orders appear: a custom order has no challan record.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.ClientOperations import order_city_payload
from aggregator.DispatchOperations import dispatch_challan_payload
from api.export_serializers import ExportDispatchReceiptSerializer
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    export_response_serializer,
)

from .GetDispatchChallansView import challan_queryset

ExportDispatchReceiptsResponseSerializer = export_response_serializer(
    "ExportDispatchReceiptsResponseSerializer", ExportDispatchReceiptSerializer
)


class ExportDispatchReceiptsView(AdminDateRangeExportView):
    """Export the complete challans of orders booked in a date window."""

    def export(self, window: DateWindow) -> list[dict]:
        orders = (
            window.created_between(challan_queryset())
            .select_related("delivery_address__city")
            .order_by("created_at", "id")
        )
        return [
            {
                **dispatch_challan_payload(order),
                "order_created_at": order.created_at.isoformat(),
                "city": order_city_payload(order),
            }
            for order in orders
        ]

    @extend_schema(
        operation_id="sales_admin_export_dispatch_receipts",
        summary="Export dispatch receipts (challans) of orders booked in a date range",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportDispatchReceiptsResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
