"""Utility endpoint: the states a client address can reference.

``GET /android/api/v1/utilities/states`` returns ``[{id, name, code,
country_id}, ...]`` ordered by country then name. Pass ``?country_id=<id>`` to
scope to one country (the usual case once the app knows which country was
picked). The app submits the matching ``state`` id to ``create-client`` /
``update-client``. Token-only; any authenticated sales person may look these
up. Soft-deleted rows are excluded.

``utilities/cities`` already returns Indian states grouped with their cities;
this endpoint is the flat, country-agnostic list for the address form's state
step.
"""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import State
from android.api.base import AndroidBaseView


class AndroidStateRefSerializer(serializers.Serializer):
    """Output shape for one state row (schema only; responses are built by hand)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    country_id = serializers.IntegerField()


class StatesView(AndroidBaseView):
    """List the states available for a client address, optionally by country."""

    @extend_schema(
        summary="List states (optionally scoped to a country)",
        parameters=[
            OpenApiParameter(
                "country_id",
                OpenApiTypes.INT,
                description="Only return states in this country.",
            )
        ],
        responses={200: AndroidStateRefSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        states = State.objects.order_by("country__name", "name")

        raw_country_id = request.query_params.get("country_id")
        if raw_country_id:
            try:
                states = states.filter(country_id=int(raw_country_id))
            except ValueError:
                raise serializers.ValidationError(
                    {"country_id": "Must be an integer."}
                ) from None

        return Response(
            [
                {
                    "id": state.id,
                    "name": state.name,
                    "code": state.code,
                    "country_id": state.country_id,
                }
                for state in states
            ]
        )
