"""Field-trip detail endpoint: ``/api/sales-admin/field-trip/<public_id>``.

``GET`` returns one trip in full -- its plan, its actual start and end, the
sales person on it, who approved it and how many farmers were recorded (the
farmers themselves are ``field-trip-farmer-visits/<public_id>``).

``DELETE`` soft deletes it, but only while it is PLANNED or APPROVED: a trip
that has started is history. 204 on success.

Soft-deleted and unknown trips are never found (404).

``FIELD_TRIP_PUBLIC_ID_PARAMETER`` is reused by every other sales-admin trip
endpoint, the way ``ORDER_PUBLIC_ID_PARAMETER`` is for orders.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import (
    delete_field_trip,
    field_trip_payload,
    field_trip_queryset,
)
from api.admin import AdminApiView
from api.field_trip_serializers import FieldTripPayloadSerializer

FIELD_TRIP_PUBLIC_ID_PARAMETER = OpenApiParameter(
    "public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The field trip's public id, e.g. FT-E79QA0E2OIHF.",
)


class FieldTripView(AdminApiView):
    """Get (GET) or delete (DELETE) one field trip (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Get a field trip in full",
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={200: FieldTripPayloadSerializer},
    )
    def get(self, request: Request, public_id: str) -> Response:
        trip = get_object_or_404(field_trip_queryset(), public_id=public_id)
        return Response(field_trip_payload(trip))

    @extend_schema(
        summary="Delete a field trip that has not started (PLANNED or APPROVED)",
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={204: None},
    )
    def delete(self, request: Request, public_id: str) -> Response:
        trip = get_object_or_404(field_trip_queryset(), public_id=public_id)
        delete_field_trip(trip, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
