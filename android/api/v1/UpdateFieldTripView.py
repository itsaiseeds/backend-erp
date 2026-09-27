"""Field-trip edit endpoint: ``PATCH /android/api/v1/edit-field-trip/<public_id>``.

The sales person changes their own trip's plan -- city, village, expected
window -- while it is PLANNED or APPROVED. Every field is optional and only
what is sent is applied.

**Editing an APPROVED trip withdraws its approval**: it goes back to PLANNED
and must be approved again, so no admin's approval stands on a plan they did
not see.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import edit_field_trip_as_owner, field_trip_payload
from android.api.base import AndroidBaseView
from android.api.field_trips import own_field_trip_or_404
from api.field_trip_serializers import FieldTripPayloadSerializer, FieldTripWriteSerializer

from .GetFieldTripFarmerVisitsView import FIELD_TRIP_PUBLIC_ID_PARAMETER


class UpdateFieldTripView(AndroidBaseView):
    """Edit the plan of the caller's PLANNED or APPROVED field trip."""

    @extend_schema(
        summary="Edit my field trip's plan (an approved trip returns to PLANNED)",
        request=FieldTripWriteSerializer(partial=True),
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={200: FieldTripPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        trip = own_field_trip_or_404(request, public_id)
        serializer = FieldTripWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        edit_field_trip_as_owner(trip, **serializer.validated_data)
        return Response(field_trip_payload(trip))
