"""Order export: ``GET /api/sales-admin/export/orders``.

Every live order **booked** (``created_at``) inside the window, oldest first,
each with its line items nested -- the packaging, the negotiated per-bag price,
the quantity and the line total. The client is named with its delivery city.
See :mod:`api.export_views` for the window contract.
"""

from __future__ import annotations

from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.models import Order, OrderItem
from aggregator.OrderOperations import order_export_payload
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    ExportResponseSerializer,
)


class ExportOrdersView(AdminDateRangeExportView):
    """Export the orders booked in a date window, with their items."""

    def export(self, window: DateWindow) -> list[dict]:
        orders = (
            window.created_between(Order.objects.all())
            .select_related("client", "status", "delivery_address__city", "transport_agency")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("product_packaging__product"),
                )
            )
            .order_by("created_at", "id")
        )
        return [order_export_payload(order) for order in orders]

    @extend_schema(
        operation_id="sales_admin_export_orders",
        summary="Export orders (with items) booked in a date range",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
