"""Inward other material update/delete endpoint: ``PATCH``/``DELETE``.

Path: ``/api/sales-admin/inward-other-material/<public_id>``.

Two jobs live here:

* **Confirm a booking.** ``PATCH`` has nothing writable: ``effective_date`` was
  stamped with today at booking and ``party`` / ``recipe`` / ``quantity`` are
  immutable. The endpoint returns the lot unchanged.
* **Correct a booking.** a wrong entry is removed with ``DELETE`` (soft) and
  re-booked. ``DELETE`` is the only corrective verb.

Soft-deleted lots are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.InwardOperations import inward_other_material_payload
from aggregator.models import InwardOtherMaterial
from api.admin import AdminApiView

from .InwardOtherMaterialsView import InwardOtherMaterialPayloadSerializer


class UpdateInwardOtherMaterialSerializer(serializers.Serializer):
    """Request validation for updating an other-material lot.

    Nothing is writable: ``effective_date`` was stamped with today at booking,
    and ``party`` / ``recipe`` / ``quantity`` are immutable -- correct a wrong
    booking by soft-deleting and re-booking.
    """


class UpdateInwardOtherMaterialView(AdminApiView):
    """Confirm a lot unchanged or soft-delete it (app admin only)."""

    serializer_class = UpdateInwardOtherMaterialSerializer
    admin_required = True

    @extend_schema(
        summary="Update an inward other-material lot (no writable fields)",
        request=UpdateInwardOtherMaterialSerializer,
        responses={200: InwardOtherMaterialPayloadSerializer},
    )
    def patch(self, request, public_id: str):
        entry = get_object_or_404(InwardOtherMaterial.objects.all(), public_id=public_id)

        serializer = UpdateInwardOtherMaterialSerializer(
            instance=entry, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        return Response(inward_other_material_payload(entry))

    @extend_schema(
        summary="Delete an inward other-material lot",
        responses={204: None},
    )
    def delete(self, request, public_id: str):
        entry = get_object_or_404(InwardOtherMaterial.objects.all(), public_id=public_id)
        entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
