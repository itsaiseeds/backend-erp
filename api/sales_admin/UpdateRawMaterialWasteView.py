"""Raw material waste edit/delete endpoint: ``PATCH`` / ``DELETE`` on one waste row.

Path: ``/api/sales-admin/raw-material-waste/<public_id>``.

``PATCH`` corrects a row's ``quantity_kg`` and/or ``reason`` (send only what
changed; the product is fixed -- delete and re-record to move waste). The new
quantity is a standing deduction from the product's unpacked raw pool, so
raising it beyond what is left unpacked is refused (400) and nothing changes;
lowering it gives kilograms back. A frozen (unusable) product cannot have its
waste edited. The stock ledger records it as ``WASTE_EDITED``.

``DELETE`` (soft) removes a wrong entry. Deleting gives the kilograms back to
the product's unpacked raw pool, which can only raise availability, so it is
never refused. Soft-deleted rows are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.InwardOperations import raw_waste_payload
from aggregator.models import RawMaterialWaste
from api.admin import AdminApiView
from api.inward_serializers import (
    RawMaterialWastePayloadSerializer,
    UpdateRawMaterialWasteSerializer,
)


class UpdateRawMaterialWasteView(AdminApiView):
    """Edit (PATCH) or soft-delete (DELETE) a raw-material waste row (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Edit a raw-material waste row (quantity / reason)",
        request=UpdateRawMaterialWasteSerializer,
        responses={200: RawMaterialWastePayloadSerializer},
    )
    def patch(self, request, public_id: str):
        entry = get_object_or_404(
            RawMaterialWaste.objects.select_related("product", "created_by"),
            public_id=public_id,
        )
        serializer = UpdateRawMaterialWasteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            entry = InventoryOperations.update_raw_waste(
                entry, actor=request.user, **serializer.validated_data
            )
        except ValueError as exc:
            raise serializers.ValidationError({"quantity_kg": str(exc)}) from None
        entry = RawMaterialWaste.objects.select_related("product", "created_by").get(pk=entry.pk)
        return Response(raw_waste_payload(entry))

    @extend_schema(summary="Delete a raw-material waste row", responses={204: None})
    def delete(self, request, public_id: str):
        entry = get_object_or_404(RawMaterialWaste.objects.all(), public_id=public_id)
        entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
