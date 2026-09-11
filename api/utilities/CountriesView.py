"""Utility endpoint: list all countries.

``GET /api/utilities/countries`` returns ``[{id, name, iso_code}, ...]``
so the frontend can render country pickers.

Restricted to an application Admin authenticated with the web session.
Soft-deleted countries are excluded.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.models import Country
from api.admin import AdminApiView


class CountrySerializer(serializers.Serializer):
    """Output shape for one country row (schema only; responses are built by hand)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    iso_code = serializers.CharField()


class CountriesView(AdminApiView):
    """List all countries, ordered by name."""

    admin_required = True

    @extend_schema(
        summary="List all countries",
        responses={200: CountrySerializer(many=True)},
    )
    def get(self, request):
        countries = Country.objects.all().order_by("name")
        payload = [
            {"id": c.id, "name": c.name, "iso_code": c.iso_code}
            for c in countries
        ]
        return Response(payload)
