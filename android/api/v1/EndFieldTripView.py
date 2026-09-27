"""End endpoint: ``POST /android/api/v1/end-field-trip/<public_id>``.

The sales person ends their IN_PROGRESS trip; ``ended_at`` is stamped with the
server's time and no more farmers can be recorded on it. Empty request body.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import end_field_trip
from aggregator.models import FieldTrip
from android.api.field_trips import OwnFieldTripTransitionView
from api.field_trip_serializers import FieldTripPayloadSerializer

from .GetFieldTripFarmerVisitsView import FIELD_TRIP_PUBLIC_ID_PARAMETER


class EndFieldTripView(OwnFieldTripTransitionView):
    """End the caller's in-progress field trip (IN_PROGRESS -> COMPLETED)."""

    @extend_schema(
        summary="End my field trip (IN_PROGRESS -> COMPLETED)",
        request=None,
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={200: FieldTripPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, trip: FieldTrip) -> None:
        end_field_trip(trip)
