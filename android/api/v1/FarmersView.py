"""Independent farmers: ``GET``/``POST`` ``/android/api/v1/farmers``.

A farmer the sales person records on their own, outside any field trip (a
``FarmerVisit`` with no trip, owned by the caller). ``GET`` lists the caller's
own, latest first, filterable by ``contact_number`` / ``farmer_name`` /
``village`` / ``is_lead`` / ``uses_our_products``; ``?all=true`` returns every
one in a single page. Farmers met on a trip stay on the field-trip endpoints.

``POST`` records one: name, 10-digit contact number, village, land held in
bigha, the crops they grow (at least one, ids from ``utilities/crops``), our
products they use (public ids from ``utilities/products``; none means they use
none) and ``is_lead`` (default false). A contact number the caller already
recorded is refused (400). 201 with the farmer.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import (
    create_independent_farmer,
    farmer_visit_payload,
    farmer_visit_queryset,
)
from aggregator.models import FarmerVisit
from android.api.field_trips import own_independent_farmers
from android.api.paginated_views import AndroidPaginatedDateRangeListView
from api.field_trip_lists import FARMER_VISIT_SORTS, INDEPENDENT_FARMER_FILTERS
from api.field_trip_serializers import (
    CreateFarmerSerializer,
    FarmerVisitPageSerializer,
    FarmerVisitPayloadSerializer,
)
from common.views.paginated_date_range import list_query_parameters


class FarmersView(AndroidPaginatedDateRangeListView):
    """List (GET) or record (POST) the caller's independent farmers."""

    serializer_class = CreateFarmerSerializer
    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = INDEPENDENT_FARMER_FILTERS
    sort_options = FARMER_VISIT_SORTS

    @extend_schema(
        operation_id="android_api_v1_farmers_list",
        summary="List the farmers I recorded outside a field trip",
        parameters=list_query_parameters(
            queryset_filters=INDEPENDENT_FARMER_FILTERS,
            sort_options=FARMER_VISIT_SORTS,
            date_window="none",
        ),
        responses={200: FarmerVisitPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet[FarmerVisit]:
        return own_independent_farmers(request)

    def serialize_page(self, page_items: list[FarmerVisit], request: Request) -> list[dict]:
        return [farmer_visit_payload(visit) for visit in page_items]

    @extend_schema(
        operation_id="android_api_v1_farmers_create",
        summary="Record a farmer outside a field trip",
        request=CreateFarmerSerializer,
        responses={201: FarmerVisitPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateFarmerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        farmer = create_independent_farmer(
            actor=request.user,
            farmer_name=data["farmer_name"],
            contact_number=data["contact_number"],
            village=data["village"],
            land_area_bigha=data["land_area_bigha"],
            crops=data["crops"],
            products=data.get("products", []),
            is_lead=data["is_lead"],
        )
        farmer = farmer_visit_queryset().get(pk=farmer.pk)
        return Response(farmer_visit_payload(farmer), status=status.HTTP_201_CREATED)
