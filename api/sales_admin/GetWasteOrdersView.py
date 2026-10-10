"""Waste-order list endpoint: ``GET /api/sales-admin/waste-orders/``.

``GET custom-orders/`` over the other kind of custom order: the same pagination /
filter / sort contract and card payload, restricted to waste orders
(``made_from_waste``). The filter pickers offer only admins, clients, products and
cities that have a waste order. ``price`` sorts on the order total (per-kg price
x kg, summed).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from api.custom_order_serializers import CustomOrderListPageSerializer
from common.views.paginated_date_range import list_query_parameters

from .GetCustomOrdersView import _SORT_OPTIONS, GetCustomOrdersView, queryset_filters

_WASTE_QUERYSET_FILTERS = queryset_filters(True)


class GetWasteOrdersView(GetCustomOrdersView):
    """List every waste order: filter by admin / client / product / city / status."""

    queryset_filters = _WASTE_QUERYSET_FILTERS
    made_from_waste = True

    @extend_schema(
        operation_id="sales_admin_get_waste_orders_list",
        summary=(
            "List waste orders (filter by sales admin / client / product / city / "
            "status, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=_WASTE_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: CustomOrderListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
