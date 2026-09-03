"""Utility endpoint: Indian states with their cities, grouped by state.

``GET /api/utilities/cities`` returns ``[{id, name, cities: [{id, name}, ...]},
...]`` -- one block per state, each state listing its cities -- so the frontend
can render hierarchical state -> city pickers and submit the matching ``city``
ids to the admin / sales-person creation endpoints.

Restricted to a Django superuser authenticated with a token (or the web
session). Soft-deleted states and cities are excluded.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from aggregator.models import City, Country, State
from api.authentication import ExpiringTokenAuthentication, SessionAuthentication
from api.permissions import IsSuperUser


class CitySerializer(serializers.Serializer):
    """Output shape for one city row (schema only; responses are built by hand)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class StateSerializer(serializers.Serializer):
    """Output shape for a state and its cities (schema only)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    cities = CitySerializer(many=True)


class CitiesView(APIView):
    """List Indian states, each with its cities, grouped by state."""

    authentication_classes: list[type] = [ExpiringTokenAuthentication, SessionAuthentication]
    permission_classes: list[type] = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        summary="List Indian states grouped with their cities",
        responses={200: StateSerializer(many=True)},
    )
    def get(self, request):
        india = (
            Country.objects.filter(name__iexact="India").first()
            or Country.objects.filter(iso_code__in=("IN", "IND", "356")).first()
        )

        states = (
            State.objects.filter(country=india).order_by("name")
            if india is not None
            else State.objects.none()
        )
        payload = []
        for state in states:
            cities = City.objects.filter(state=state).order_by("name")
            payload.append(
                {
                    "id": state.id,
                    "name": state.name,
                    "cities": [{"id": city.id, "name": city.name} for city in cities],
                }
            )
        return Response(payload)
