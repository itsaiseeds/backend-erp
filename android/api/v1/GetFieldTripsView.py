"""Field-trip list endpoint: ``GET /android/api/v1/get-field-trips``.

The calling sales person's trips, latest planned start first. Scoped to the
caller: the queryset starts from their own trips, so no filter can widen it to
somebody else's, and the city picker lists only cities they have trips to.

Filters and sorts are shared with the sales-admin list
(``api.field_trip_lists``):

* ``?status=<CODE,...>`` -- ``PLANNED`` / ``APPROVED`` / ``IN_PROGRESS`` /
  ``COMPLETED``.
* ``?city_id=<id,...>`` -- trips to those cities (see options).
* ``?village=<term>`` -- case-insensitive substring of the village.
* ``?expected_start_gte=`` / ``?expected_start_lte=`` -- planned start window.
* ``?sort=<-?name,...>`` over ``expected_start_at`` / ``created_at``.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.FieldTripOperations import field_trip_payload
from aggregator.models import FieldTrip
from android.api.field_trips import own_field_trips
from android.api.paginated_views import AndroidPaginatedDateRangeListView
from api.field_trip_lists import FIELD_TRIP_SORTS, field_trip_filters
from api.field_trip_serializers import FieldTripPageSerializer
from common.views.paginated_date_range import list_query_parameters

_QUERYSET_FILTERS = field_trip_filters(own_field_trips, by_sales_person=False)


class GetFieldTripsView(AndroidPaginatedDateRangeListView):
    """List the caller's field trips: filter by status / city / village / dates."""

    enforce_date_range_filters = False
    default_sort = "-expected_start_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = FIELD_TRIP_SORTS

    @extend_schema(
        operation_id="android_api_v1_get_field_trips_list",
        summary="List my field trips (filter by status / city / village / dates)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=FIELD_TRIP_SORTS,
            date_window="none",
        ),
        responses={200: FieldTripPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet[FieldTrip]:
        return own_field_trips(request)

    def serialize_page(self, page_items: list[FieldTrip], request: Request) -> list[dict]:
        return [field_trip_payload(trip) for trip in page_items]
