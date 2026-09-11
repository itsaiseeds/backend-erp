"""Utility endpoint: list states, optionally filtered by country.

``GET /api/utilities/states`` returns ``[{id, name, code, country: {id, name}},
...]``.  Pass ``?country=<id>`` to narrow to one country.

Restricted to an application Admin authenticated with the web session.
Soft-deleted states and countries are excluded.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.models import State
from api.admin import AdminApiView


class CountryRefSerializer(serializers.Serializer):
    """Output shape for the country inside a state row."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class StateSerializer(serializers.Serializer):
    """Output shape for one state row."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField(allow_null=True)
    country = CountryRefSerializer()


class StatesView(AdminApiView):
    """List states, optionally filtered by country id."""

    admin_required = True

    @extend_schema(
        summary="List states (optionally filtered by country)",
        parameters=[
            OpenApiParameter(
                name="country",
                type=int,
                required=False,
                description="Filter states by country id",
            )
        ],
        responses={200: StateSerializer(many=True)},
    )
    def get(self, request):
        qs = State.objects.select_related("country").all().order_by(
            "country__name", "name"
        )
        country_id = request.query_params.get("country")
        if country_id is not None:
            qs = qs.filter(country_id=country_id)

        payload = [
            {
                "id": s.id,
                "name": s.name,
                "code": s.code,
                "country": {"id": s.country_id, "name": s.country.name},
            }
            for s in qs
        ]
        return Response(payload)
