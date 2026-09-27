"""Delete endpoint: ``DELETE /android/api/v1/delete-field-trip/<public_id>``.

The sales person deletes their own trip, but only while it is PLANNED or
APPROVED -- a trip that has started is history (``FieldTrip.mark_deleted``
refuses it, a 400). Soft delete; 204 on success.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import delete_field_trip
from android.api.base import AndroidBaseView
from android.api.field_trips import own_field_trip_or_404

from .GetFieldTripFarmerVisitsView import FIELD_TRIP_PUBLIC_ID_PARAMETER


class DeleteFieldTripView(AndroidBaseView):
    """Delete the caller's field trip that has not started."""

    @extend_schema(
        summary="Delete my field trip (PLANNED or APPROVED only)",
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={204: None},
    )
    def delete(self, request: Request, public_id: str) -> Response:
        delete_field_trip(own_field_trip_or_404(request, public_id), request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
