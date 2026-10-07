"""Ownership scoping shared by the Android field-trip endpoints.

Every trip lookup on the app starts from the caller's own trips, so another
sales person's trip is simply not found (404) -- no endpoint can reach it, and
none has to remember to check.
"""

from __future__ import annotations

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import (
    farmer_visit_queryset,
    field_trip_payload,
    field_trip_queryset,
)
from aggregator.models import FarmerVisit, FieldTrip

from .base import AndroidBaseView


def own_field_trips(request: Request) -> QuerySet[FieldTrip]:
    """The caller's trips, joined for a trip payload."""
    return field_trip_queryset().filter(created_by=request.user)


def own_field_trip_or_404(request: Request, public_id: str) -> FieldTrip:
    """One of the caller's trips, or 404 -- including for somebody else's."""
    return get_object_or_404(own_field_trips(request), public_id=public_id)


def own_farmer_visit_or_404(request: Request, public_id: str) -> FarmerVisit:
    """A farmer recorded on one of the caller's trips, or 404 -- including for somebody else's."""
    return get_object_or_404(
        farmer_visit_queryset()
        .select_related("field_trip__status")
        .filter(field_trip__created_by=request.user),
        public_id=public_id,
    )


def own_independent_farmers(request: Request) -> QuerySet[FarmerVisit]:
    """The caller's farmers recorded outside any trip, with their crops and products."""
    return farmer_visit_queryset().filter(field_trip__isnull=True, created_by=request.user)


def own_independent_farmer_or_404(request: Request, public_id: str) -> FarmerVisit:
    """One of the caller's independent farmers, or 404 -- a trip visit or somebody else's too."""
    return get_object_or_404(own_independent_farmers(request), public_id=public_id)


class OwnFieldTripTransitionView(AndroidBaseView):
    """One lifecycle verb on the caller's own trip: load, apply, return the trip.

    The Android counterpart of ``api.sales_admin.FieldTripTransitionView``; the
    status guards live in ``aggregator.FieldTripOperations``.
    """

    def apply_transition(self, trip: FieldTrip) -> None:
        """Move ``trip`` to its new status. Implemented by each subclass."""
        raise NotImplementedError(
            f"{type(self).__name__} must implement apply_transition(self, trip)."
        )

    def transition(self, request: Request, public_id: str) -> Response:
        trip = own_field_trip_or_404(request, public_id)
        self.apply_transition(trip)
        return Response(field_trip_payload(trip))
