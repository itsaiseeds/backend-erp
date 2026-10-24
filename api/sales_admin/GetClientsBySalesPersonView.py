"""One sales person's clients: ``GET /api/sales-admin/client/by-sales-person/<id>``.

``<id>`` is the ``SalesPerson`` id. A sales person who has since been removed is
still found (404 only for an unknown id) -- the point is to see which clients
need a new owner, then move them with ``POST client/transfer-client/``. Same
card, filters, sorts and pagination as ``get-clients/``.
"""

from __future__ import annotations

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from authentication.models import SalesPerson
from common.views.paginated_date_range import list_query_parameters

from .GetClientsView import (
    _QUERYSET_FILTERS,
    _SORT_OPTIONS,
    ClientListPageSerializer,
    GetClientsView,
)


class GetClientsBySalesPersonView(GetClientsView):
    """List the live clients owned by one sales person."""

    @extend_schema(
        operation_id="sales_admin_get_clients_by_sales_person",
        summary="List one sales person's clients",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: ClientListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        salesperson = get_object_or_404(
            SalesPerson.all_objects.select_related("user"), id=self.kwargs["id"]
        )
        return super().get_queryset(request).filter(created_by=salesperson.user)
