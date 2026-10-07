"""Farmer-visit creation endpoint: ``POST /android/api/v1/create-farmer-visit``.

The sales person records a farmer they met on one of their own trips, while it
is IN_PROGRESS: name, 10-digit contact number, village (defaults to the trip's),
land held in bigha, the crops they grow (at least one, ids from
``utilities/crops``) and our products they use (public ids from
``utilities/products``; an empty list means they use none).

A contact number already recorded on the same trip is refused -- it guards
against the app resubmitting the same farmer on a flaky connection.
201 with the visit payload.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import (
    create_farmer_visit,
    farmer_visit_payload,
    farmer_visit_queryset,
)
from android.api.base import AndroidBaseView
from android.api.field_trips import own_field_trip_or_404
from api.field_trip_serializers import CreateFarmerVisitSerializer, FarmerVisitPayloadSerializer


class CreateFarmerVisitView(AndroidBaseView):
    """Record a farmer met on the caller's in-progress field trip."""

    @extend_schema(
        summary="Record a farmer met on my in-progress field trip",
        request=CreateFarmerVisitSerializer,
        responses={201: FarmerVisitPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateFarmerVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        trip = own_field_trip_or_404(request, data["field_trip_public_id"])
        visit = create_farmer_visit(
            trip,
            actor=request.user,
            farmer_name=data["farmer_name"],
            contact_number=data["contact_number"],
            village=data["village"],
            land_area_bigha=data["land_area_bigha"],
            crops=data["crops"],
            products=data.get("products", []),
            is_lead=data["is_lead"],
        )
        visit = farmer_visit_queryset().get(id=visit.id)
        return Response(farmer_visit_payload(visit), status=status.HTTP_201_CREATED)
