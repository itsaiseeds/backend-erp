"""Approval endpoint: ``POST /api/sales-admin/approve-field-trip/<public_id>``.

A sales admin approves a PLANNED trip, recording who approved it and when. Only
an approved trip can be started from the app. An empty request body is
expected; the trip is named in the path.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import approve_field_trip
from aggregator.models import FieldTrip
from api.field_trip_serializers import FieldTripPayloadSerializer

from .FieldTripTransitionView import FieldTripTransitionView
from .FieldTripView import FIELD_TRIP_PUBLIC_ID_PARAMETER


class ApproveFieldTripView(FieldTripTransitionView):
    """Approve a planned field trip (PLANNED -> APPROVED)."""

    @extend_schema(
        summary="Approve a field trip (PLANNED -> APPROVED)",
        request=None,
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={200: FieldTripPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, trip: FieldTrip, request: Request) -> None:
        approve_field_trip(trip, request.user)
