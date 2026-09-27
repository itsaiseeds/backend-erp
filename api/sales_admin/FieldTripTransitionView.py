"""Shared base for the sales-admin field-trip lifecycle endpoints.

``approve-field-trip`` and ``unapprove-field-trip`` differ only in which
operations function they call; loading the trip and returning its payload are
the same, so they live here -- the field-trip counterpart of
``OrderTransitionView``.

Which statuses a verb may be applied from is decided in
``aggregator.FieldTripOperations``, beside the transition itself; a refused
transition raises ``ValidationError`` there, rendered as a 400.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import field_trip_payload, field_trip_queryset
from aggregator.models import FieldTrip
from api.admin import AdminApiView


class FieldTripTransitionView(AdminApiView):
    """One field-trip lifecycle verb: load, apply the transition, return the trip."""

    admin_required = True

    def apply_transition(self, trip: FieldTrip, request: Request) -> None:
        """Move ``trip`` to its new status. Implemented by each subclass."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement apply_transition(self, trip, request)."
        )

    def transition(self, request: Request, public_id: str) -> Response:
        trip = get_object_or_404(field_trip_queryset(), public_id=public_id)
        self.apply_transition(trip, request)
        return Response(field_trip_payload(trip))
