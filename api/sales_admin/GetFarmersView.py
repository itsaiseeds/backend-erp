"""Farmer list endpoint: ``GET /api/sales-admin/farmers/``.

Every farmer recorded on **any** field trip, by any sales person -- the list a
sales admin reads to know the farmers behind the trips. A farmer is one
``contact_number``: a visit is a meeting, so the same farmer met on three trips
is three ``FarmerVisit`` rows and one row here, carrying their latest visit's
name / village / city / land area and their crops, products, sales people and
meeting history merged over all of them
(``aggregator.FieldTripOperations.farmer_payload``).

Paginated (``?all=true`` for every farmer in one page), newest visit first.
Filterable by ``?contact_number=`` / ``?farmer_name=`` / ``?village=`` /
``?city_id=`` / ``?created_by=`` / ``?crop=`` / ``?product=`` /
``?uses_our_products=`` and sortable by ``farmer_name`` / ``last_visited_at`` /
``visit_count`` / ``land_area`` -- see ``api.field_trip_lists``. Every filter
matches a farmer on *any* of their visits, not only the latest.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.FieldTripOperations import (
    farmer_payload,
    farmer_queryset,
    farmer_visits_by_contact,
)
from aggregator.models import FarmerVisit
from api.field_trip_lists import ALL_FARMER_FILTERS, FARMER_SORTS
from api.field_trip_serializers import FarmerPageSerializer
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import list_query_parameters


class GetFarmersView(AdminPaginatedDateRangeListView):
    """List every farmer recorded on any field trip."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = ALL_FARMER_FILTERS
    sort_options = FARMER_SORTS

    @extend_schema(
        operation_id="sales_admin_get_farmers_list",
        summary="List every farmer recorded on a field trip (all trips, deduped by contact)",
        parameters=list_query_parameters(
            queryset_filters=ALL_FARMER_FILTERS,
            sort_options=FARMER_SORTS,
            date_window="none",
        ),
        responses={200: FarmerPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet[FarmerVisit]:
        return farmer_queryset()

    def serialize_page(self, page_items: list[FarmerVisit], request: Request) -> list[dict]:
        by_contact = farmer_visits_by_contact(visit.contact_number for visit in page_items)
        return [
            farmer_payload(visit, by_contact.get(visit.contact_number, [visit]))
            for visit in page_items
        ]
