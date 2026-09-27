"""Field-trip list endpoint: ``GET /api/sales-admin/field-trips/``.

Every sales person's trips, latest planned start first, each as a full trip
payload. The sales-admin counterpart of ``GET /android/api/v1/get-field-trips``:
the same filters and sorts (``api.field_trip_lists``) plus ``?created_by=`` to
narrow to one sales person, with option lists drawn from every trip.

* ``?created_by=<id,...>`` -- trips of those sales people (see options).
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

from aggregator.FieldTripOperations import field_trip_payload, field_trip_queryset
from aggregator.models import FieldTrip
from api.field_trip_lists import FIELD_TRIP_SORTS, field_trip_filters
from api.field_trip_serializers import FieldTripPageSerializer
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import list_query_parameters

_QUERYSET_FILTERS = field_trip_filters(
    lambda request: FieldTrip.objects.all(), by_sales_person=True
)


class GetFieldTripsView(AdminPaginatedDateRangeListView):
    """List every field trip: filter by sales person / status / city / village / dates."""

    enforce_date_range_filters = False
    default_sort = "-expected_start_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = FIELD_TRIP_SORTS

    @extend_schema(
        operation_id="sales_admin_get_field_trips_list",
        summary="List field trips (filter by sales person / status / city / village / dates)",
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
        return field_trip_queryset()

    def serialize_page(self, page_items: list[FieldTrip], request: Request) -> list[dict]:
        return [field_trip_payload(trip) for trip in page_items]
