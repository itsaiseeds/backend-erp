"""Utility endpoint: the countries a client address can reference.

``GET /android/api/v1/utilities/countries`` returns ``[{id, name, iso_code},
...]`` ordered by name, so the sales-person app can offer a country picker and
submit the matching ``country`` id to ``create-client`` / ``update-client``
(which take the pk, not the name). Token-only; any authenticated sales person
may look these up. Soft-deleted rows are excluded.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Country
from android.api.base import AndroidBaseView


class AndroidCountrySerializer(serializers.Serializer):
    """Output shape for one country row (schema only; responses are built by hand)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    iso_code = serializers.CharField()


class CountriesView(AndroidBaseView):
    """List the countries available for a client address."""

    @extend_schema(
        summary="List countries",
        responses={200: AndroidCountrySerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        return Response(
            [
                {"id": country.id, "name": country.name, "iso_code": country.iso_code}
                for country in Country.objects.order_by("name")
            ]
        )
