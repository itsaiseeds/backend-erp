"""Farmer-visit list endpoint:
``GET /android/api/v1/field-trip-farmer-visits/<public_id>``.

The farmers recorded on one of the caller's own trips, latest first. Another
sales person's trip is a 404. Same filters and sorts as the sales-admin list
(``api.field_trip_lists``); ``?all=true`` returns the whole trip in one page.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request

from aggregator.FieldTripOperations import farmer_visit_payload, farmer_visit_queryset
from aggregator.models import FarmerVisit
from android.api.field_trips import own_field_trip_or_404
from android.api.paginated_views import AndroidPaginatedDateRangeListView
from api.field_trip_lists import FARMER_VISIT_FILTERS, FARMER_VISIT_SORTS
from api.field_trip_serializers import FarmerVisitPageSerializer
from common.views.paginated_date_range import list_query_parameters

FIELD_TRIP_PUBLIC_ID_PARAMETER = OpenApiParameter(
    "public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The public id of one of your field trips, e.g. FT-E79QA0E2OIHF.",
)


class GetFieldTripFarmerVisitsView(AndroidPaginatedDateRangeListView):
    """List the farmers recorded on one of the caller's field trips."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = FARMER_VISIT_FILTERS
    sort_options = FARMER_VISIT_SORTS

    @extend_schema(
        operation_id="android_api_v1_get_field_trip_farmer_visits_list",
        summary="List the farmers recorded on my field trip",
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
        trip = own_field_trip_or_404(request, self.kwargs["public_id"])
        return farmer_visit_queryset().filter(field_trip=trip)

    def serialize_page(self, page_items: list[FarmerVisit], request: Request) -> list[dict]:
        return [farmer_visit_payload(visit) for visit in page_items]
