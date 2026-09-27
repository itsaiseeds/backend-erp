"""Unapproval endpoint: ``POST /api/sales-admin/unapprove-field-trip/<public_id>``.

Reverses ``approve-field-trip``: an APPROVED trip goes back to PLANNED and its
``approved_by`` / ``approved_at`` are cleared. Refused once the trip has
started -- an IN_PROGRESS or COMPLETED trip keeps the approval it ran under.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import unapprove_field_trip
from aggregator.models import FieldTrip
from api.field_trip_serializers import FieldTripPayloadSerializer

from .FieldTripTransitionView import FieldTripTransitionView
from .FieldTripView import FIELD_TRIP_PUBLIC_ID_PARAMETER


class UnapproveFieldTripView(FieldTripTransitionView):
    """Withdraw a field trip's approval before it starts (APPROVED -> PLANNED)."""

    @extend_schema(
        summary="Unapprove a field trip (APPROVED -> PLANNED)",
        request=None,
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={200: FieldTripPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, trip: FieldTrip, request: Request) -> None:
        unapprove_field_trip(trip)
