"""Utility endpoint: list the cities of a given state.

``GET /api/utilities/cities?state=Maharashtra`` returns that state's cities as
``[{"id": ..., "name": ...}, ...]`` so the frontend can render both the picker
labels and the ``city`` ids it later submits to ``/api/sales_admin``.

Public (no auth): the city picker can be rendered before login. The state match
is case-insensitive; an unknown state gives ``404`` and a missing ``state``
query parameter gives ``400``.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from aggregator.models import City, State


class CitySerializer(serializers.Serializer):
    """Output shape for one city row (schema only; responses are built by hand)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class CitiesByStateView(APIView):
    """Public city look-up for the state -> city pickers."""

    authentication_classes: list[type] = []
    permission_classes: list[type] = [AllowAny]

    @extend_schema(
        summary="List cities of a state",
        parameters=[
            OpenApiParameter(
                name="state",
                type=str,
                description="State name (case-insensitive), e.g. 'Maharashtra'.",
                required=True,
            )
        ],
        responses={
            200: CitySerializer(many=True),
            400: OpenApiResponse(description="The 'state' query parameter is required."),
            404: OpenApiResponse(description="No state matched the given name."),
        },
    )
    def get(self, request):
        state_name = (request.query_params.get("state") or "").strip()
        if not state_name:
            return Response(
                {"detail": "The 'state' query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = State.objects.filter(name__iexact=state_name).first()
        if state is None:
            return Response(
                {"detail": f"State '{state_name}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        cities = City.objects.filter(state=state)
        return Response([{"id": city.id, "name": city.name} for city in cities])
