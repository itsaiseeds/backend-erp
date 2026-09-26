"""Party update/delete endpoint: ``PATCH``/``DELETE`` ``/api/sales-admin/parties/<id>``.

Only an application Admin may update or delete a party. Soft-deleted parties are
never found (404). ``name`` + ``city`` are validated for uniqueness, excluding
the party being edited.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.InwardOperations import party_payload
from aggregator.models import City, Party
from api.admin import AdminApiView

from .PartiesView import PartyPayloadSerializer


class UpdatePartySerializer(serializers.Serializer):
    """Request validation for updating a ``Party`` (all fields optional)."""

    name = serializers.CharField(
        max_length=255,
        required=False,
        error_messages={"blank": "Party name may not be blank."},
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False
    )

    def validate_name(self, value):
        return value.strip()

    def validate(self, attrs):
        name = attrs.get("name", self.instance.name if self.instance is not None else None)
        city = attrs.get("city", self.instance.city if self.instance is not None else None)
        if name is not None and city is not None:
            qs = Party.all_objects.filter(name=name, city=city)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "A party with this name already exists in this city."
                )
            attrs["name"] = name
        return attrs


class UpdatePartyView(AdminApiView):
    """Update or delete a single party (app admin only)."""

    serializer_class = UpdatePartySerializer
    admin_required = True

    @extend_schema(
        summary="Update a party",
        request=UpdatePartySerializer,
        responses={200: PartyPayloadSerializer},
    )
    def patch(self, request, id: int):
        party = get_object_or_404(Party.objects.all(), pk=id)

        serializer = UpdatePartySerializer(instance=party, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changed = False
        for field in ("name", "city"):
            if field in serializer.validated_data:
                setattr(party, field, serializer.validated_data[field])
                changed = True
        if changed:
            party.save()
        return Response(party_payload(party))

    @extend_schema(
        summary="Delete a party",
        responses={204: None},
    )
    def delete(self, request, id: int):
        party = get_object_or_404(Party.objects.all(), pk=id)
        party.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
