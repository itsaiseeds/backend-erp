"""Field-trip edit endpoint: ``PATCH /api/sales-admin/edit-field-trip/<public_id>``.

A sales admin corrects a trip's plan -- its city, village and expected window --
but only **before approving it**: once approved, the plan is what was signed
off, so an admin who wants to change it unapproves first. Every field is
optional and only what is sent is applied.

Status, approval and the actual start/end times are not fields here: each has
its own verb.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.FieldTripOperations import (
    edit_field_trip_as_admin,
    field_trip_payload,
    field_trip_queryset,
)
from api.admin import AdminApiView
from api.field_trip_serializers import FieldTripPayloadSerializer, FieldTripWriteSerializer

from .FieldTripView import FIELD_TRIP_PUBLIC_ID_PARAMETER


class UpdateFieldTripView(AdminApiView):
    """Edit a PLANNED field trip's plan (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Edit a field trip's plan (PLANNED only)",
        request=FieldTripWriteSerializer(partial=True),
        parameters=[FIELD_TRIP_PUBLIC_ID_PARAMETER],
        responses={200: FieldTripPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        trip = get_object_or_404(field_trip_queryset(), public_id=public_id)
        serializer = FieldTripWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        edit_field_trip_as_admin(trip, **serializer.validated_data)
        return Response(field_trip_payload(trip))
