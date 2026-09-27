"""Start endpoint: ``POST /android/api/v1/start-field-trip/<public_id>``.

The sales person starts their APPROVED trip; ``started_at`` is stamped with the
server's time. A sales person runs one trip at a time, so starting is refused
while another of theirs is still IN_PROGRESS. Empty request body.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import start_field_trip
from aggregator.models import FieldTrip
from android.api.field_trips import OwnFieldTripTransitionView
from api.field_trip_serializers import FieldTripPayloadSerializer

from .GetFieldTripFarmerVisitsView import FIELD_TRIP_PUBLIC_ID_PARAMETER


class StartFieldTripView(OwnFieldTripTransitionView):
    """Start the caller's approved field trip (APPROVED -> IN_PROGRESS)."""

    @extend_schema(
        summary="Start my field trip (APPROVED -> IN_PROGRESS)",
        request=None,
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={200: FieldTripPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, trip: FieldTrip) -> None:
        start_field_trip(trip)
