"""One independent farmer: ``GET``/``PATCH``/``DELETE`` ``/android/api/v1/farmer/<public_id>``.

The caller's own farmer recorded outside any field trip (``FV-…``). Another
sales person's farmer, or a farmer met on a trip, is a 404.

``PATCH`` corrects any subset of name, contact number, village, land, ``is_lead``,
crops and products (a field that is sent may not be blank; at least one crop
remains). ``DELETE`` soft-deletes the farmer (204).
"""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import (
    delete_independent_farmer,
    farmer_visit_payload,
    farmer_visit_queryset,
    update_farmer_visit,
)
from android.api.base import AndroidBaseView
from android.api.field_trips import own_independent_farmer_or_404
from api.field_trip_serializers import EditFarmerVisitSerializer, FarmerVisitPayloadSerializer

FARMER_PUBLIC_ID_PARAMETER = OpenApiParameter(
    "public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The farmer's public id (FV-…).",
)


class FarmerDetailView(AndroidBaseView):
    """Read, edit or delete one of the caller's independent farmers."""

    @extend_schema(
        operation_id="android_api_v1_farmer_retrieve",
        summary="Get one farmer I recorded outside a field trip",
        parameters=[FARMER_PUBLIC_ID_PARAMETER],
        responses={200: FarmerVisitPayloadSerializer},
    )
    def get(self, request: Request, public_id: str) -> Response:
        return Response(farmer_visit_payload(own_independent_farmer_or_404(request, public_id)))

    @extend_schema(
        operation_id="android_api_v1_farmer_update",
        summary="Edit a farmer I recorded outside a field trip",
        request=EditFarmerVisitSerializer,
        parameters=[FARMER_PUBLIC_ID_PARAMETER],
        responses={200: FarmerVisitPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        farmer = own_independent_farmer_or_404(request, public_id)
        serializer = EditFarmerVisitSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_farmer_visit(farmer, actor=request.user, **serializer.validated_data)
        farmer = farmer_visit_queryset().get(pk=farmer.pk)
        return Response(farmer_visit_payload(farmer))

    @extend_schema(
        operation_id="android_api_v1_farmer_delete",
        summary="Delete a farmer I recorded outside a field trip",
        parameters=[FARMER_PUBLIC_ID_PARAMETER],
        responses={204: None},
    )
    def delete(self, request: Request, public_id: str) -> Response:
        delete_independent_farmer(own_independent_farmer_or_404(request, public_id), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
