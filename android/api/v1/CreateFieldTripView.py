"""Field-trip creation endpoint: ``POST /android/api/v1/create-field-trip``.

A sales person plans a trip to a village: the city (an id from
``utilities/cities``), the village, and when they expect to start and finish.
The trip is born PLANNED and must be approved by a sales admin before it can be
started. 201 with the trip payload.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import create_field_trip, field_trip_payload
from android.api.base import AndroidBaseView
from android.api.field_trips import own_field_trip_or_404
from api.field_trip_serializers import FieldTripPayloadSerializer, FieldTripWriteSerializer


class CreateFieldTripView(AndroidBaseView):
    """Plan a field trip (born PLANNED)."""

    @extend_schema(
        summary="Plan a field trip",
        request=FieldTripWriteSerializer,
        responses={201: FieldTripPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = FieldTripWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = create_field_trip(sales_person=request.user, **serializer.validated_data)
        # Reload through the payload queryset for the joins and the visit count.
        trip = own_field_trip_or_404(request, trip.public_id)
        return Response(field_trip_payload(trip), status=status.HTTP_201_CREATED)
