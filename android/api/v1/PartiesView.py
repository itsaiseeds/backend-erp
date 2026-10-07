"""Utility endpoint: every party, ``GET /android/api/v1/utilities/parties``.

The flat, unpaginated supplier picker for booking inward lots (rows built with
``InwardOperations.party_payload``). Token-only; open to either Android role,
like every ``utilities/`` route. Soft-deleted parties are excluded.
``?type=RAW_MATERIAL`` / ``?type=OTHER_MATERIAL`` narrows the list to the
parties a raw / other-material lot may be booked against; an unknown type is a
400.
"""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import party_payload
from aggregator.models import Party, PartyType
from android.api.base import AndroidSharedView
from api.inward_serializers import parse_party_type


class UtilityPartyCityRefSerializer(serializers.Serializer):
    """Output shape for the ``city`` reference on a party (schema only)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class UtilityPartySerializer(serializers.Serializer):
    """Output shape for one party row (schema only)."""

    id = serializers.IntegerField(help_text="Send this as party.")
    name = serializers.CharField()
    city = UtilityPartyCityRefSerializer()
    party_type = serializers.ChoiceField(choices=PartyType.choices)
    contact_number = serializers.CharField(allow_null=True)


class PartiesView(AndroidSharedView):
    """List every party, optionally of one type."""

    @extend_schema(
        summary="List every party (not paginated; filter by type)",
        parameters=[
            OpenApiParameter(
                "type",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=False,
                enum=PartyType.values,
                description="Only parties of this type.",
            )
        ],
        responses={200: UtilityPartySerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        parties = Party.objects.select_related("city").order_by("name", "id")
        raw_type = request.query_params.get("type")
        if raw_type is not None:
            try:
                party_type = parse_party_type(raw_type)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"type": exc.detail}) from None
            parties = parties.filter(party_type=party_type)
        return Response([party_payload(party) for party in parties])
