"""Farmer-visit list endpoint:
``GET /api/sales-admin/field-trip-farmer-visits/<public_id>``.

The farmers recorded on one trip, latest first: name, contact, village, land
held, the crops they grow and the products of ours they use. Paginated
(``?all=true`` for the whole trip in one page), filterable by ``?crop=`` /
``?product=`` / ``?uses_our_products=`` and sortable by ``created_at`` /
``land_area`` / ``farmer_name`` -- see ``api.field_trip_lists``.

An unknown trip is a 404, not an empty page.
"""

from __future__ import annotations

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.FieldTripOperations import farmer_visit_payload, farmer_visit_queryset
from aggregator.models import FarmerVisit, FieldTrip
from api.field_trip_lists import FARMER_VISIT_FILTERS, FARMER_VISIT_SORTS
from api.field_trip_serializers import FarmerVisitPageSerializer
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import list_query_parameters

from .FieldTripView import FIELD_TRIP_PUBLIC_ID_PARAMETER


class GetFieldTripFarmerVisitsView(AdminPaginatedDateRangeListView):
    """List the farmers recorded on one field trip (app admin only)."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = FARMER_VISIT_FILTERS
    sort_options = FARMER_VISIT_SORTS

    @extend_schema(
        operation_id="sales_admin_get_field_trip_farmer_visits_list",
        summary="List the farmers recorded on a field trip",
        parameters=[
            FIELD_TRIP_PUBLIC_ID_PARAMETER,
            *list_query_parameters(
                queryset_filters=FARMER_VISIT_FILTERS,
                sort_options=FARMER_VISIT_SORTS,
                date_window="none",
            ),
        ],
        responses={200: FarmerVisitPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet[FarmerVisit]:
        trip = get_object_or_404(FieldTrip.objects.all(), public_id=self.kwargs["public_id"])
        return farmer_visit_queryset().filter(field_trip=trip)

    def serialize_page(self, page_items: list[FarmerVisit], request: Request) -> list[dict]:
        return [farmer_visit_payload(visit) for visit in page_items]
