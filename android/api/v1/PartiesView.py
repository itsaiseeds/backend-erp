"""Utility endpoint: every party, ``GET /android/api/v1/utilities/parties``.

The flat, unpaginated supplier picker for booking inward lots (rows built with
``InwardOperations.party_payload``). Token-only; open to either Android role,
like every ``utilities/`` route. Soft-deleted parties are excluded.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import party_payload
from aggregator.models import Party
from android.api.base import AndroidSharedView


class UtilityPartyCityRefSerializer(serializers.Serializer):
    """Output shape for the ``city`` reference on a party (schema only)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class UtilityPartySerializer(serializers.Serializer):
    """Output shape for one party row (schema only)."""

    id = serializers.IntegerField(help_text="Send this as party.")
    name = serializers.CharField()
    city = UtilityPartyCityRefSerializer()
    contact_number = serializers.CharField(allow_null=True)


class PartiesView(AndroidSharedView):
    """List every party."""

    @extend_schema(
        summary="List every party (not paginated)",
        responses={200: UtilityPartySerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        parties = Party.objects.select_related("city").order_by("name", "id")
        return Response([party_payload(party) for party in parties])
