"""Rejected-order list endpoint: ``GET /api/sales-admin/rejected-orders/``.

``GET waste-orders/`` over rejected orders (``order_kind`` rejected): the same
pagination / filter / sort contract and card payload. The filter pickers offer
only admins, clients, products and cities that have a rejected order.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from api.custom_order_serializers import CustomOrderListPageSerializer
from common.views.paginated_date_range import list_query_parameters

from .GetCustomOrdersView import _SORT_OPTIONS, GetCustomOrdersView, queryset_filters

_REJECTED_QUERYSET_FILTERS = queryset_filters("rejected")


class GetRejectedOrdersView(GetCustomOrdersView):
    """List every rejected order: filter by admin / client / product / city / status."""

    queryset_filters = _REJECTED_QUERYSET_FILTERS
    order_kind = "rejected"

    @extend_schema(
        operation_id="sales_admin_get_rejected_orders_list",
        summary=(
            "List rejected orders (filter by sales admin / client / product / city / "
            "status, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=_REJECTED_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: CustomOrderListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
