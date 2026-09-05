"""Utility endpoint: Indian states with their cities, grouped by state.

``GET /android/api/v1/utilities/cities`` returns ``[{id, name, cities: [{id,
name}, ...]}, ...]`` -- one block per state, each state listing its cities --
so the sales person app can render hierarchical state -> city pickers.
Token-only (see
``api.utilities.CitiesView`` for the web counterpart, which is session-only and
superuser-restricted there); here any authenticated sales person may look up
cities. Soft-deleted states and cities are excluded.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.models import City, Country, State
from android.api.base import AndroidBaseView


class AndroidCitySerializer(serializers.Serializer):
    """Output shape for one city row (schema only; responses are built by hand)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class AndroidStateSerializer(serializers.Serializer):
    """Output shape for a state and its cities (schema only)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    cities = AndroidCitySerializer(many=True)


class CitiesView(AndroidBaseView):
    """List Indian states, each with its cities, grouped by state."""

    @extend_schema(
        summary="List Indian states grouped with their cities",
        responses={200: AndroidStateSerializer(many=True)},
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
