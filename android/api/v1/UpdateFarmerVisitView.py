"""Farmer-visit edit endpoint: ``PATCH /android/api/v1/edit-farmer-visit/<public_id>``.

The sales person corrects the **name** of a farmer they recorded -- and only
that, and only while the trip the farmer was recorded on is IN_PROGRESS. A
farmer on someone else's trip is a 404; on a trip in any other status, a 400.
"""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import farmer_visit_payload, rename_farmer_visit
from android.api.base import AndroidBaseView
from android.api.field_trips import own_farmer_visit_or_404
from api.field_trip_serializers import EditFarmerVisitSerializer, FarmerVisitPayloadSerializer

FARMER_VISIT_PUBLIC_ID_PARAMETER = OpenApiParameter(
    "public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The farmer visit's public id (FV-…).",
)


class UpdateFarmerVisitView(AndroidBaseView):
    """Rename a farmer recorded on the caller's in-progress field trip."""

    @extend_schema(
        summary="Rename a farmer on my in-progress field trip",
        request=EditFarmerVisitSerializer,
        parameters=[FARMER_VISIT_PUBLIC_ID_PARAMETER],
        responses={200: FarmerVisitPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        visit = own_farmer_visit_or_404(request, public_id)
        serializer = EditFarmerVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rename_farmer_visit(visit, serializer.validated_data["farmer_name"])
        return Response(farmer_visit_payload(visit))
