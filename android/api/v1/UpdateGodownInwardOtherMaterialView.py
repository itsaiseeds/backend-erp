"""Godown inward other-material lot: PATCH/DELETE ``godown/inward-other-material/<public_id>``.

Path: ``/android/api/v1/godown/inward-other-material/<public_id>``.

The Android counterpart of ``api.sales_admin.UpdateInwardOtherMaterialView``:
``PATCH`` has nothing writable and returns the lot unchanged; ``DELETE`` (soft)
is the only corrective verb. Godown-manager token only; soft-deleted lots are a
404.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import inward_other_material_payload
from aggregator.models import InwardOtherMaterial
from android.api.base import AndroidGodownBaseView
from api.inward_serializers import (
    InwardOtherMaterialPayloadSerializer,
    UpdateInwardOtherMaterialSerializer,
)


class UpdateGodownInwardOtherMaterialView(AndroidGodownBaseView):
    """Confirm a lot unchanged or soft-delete it (godown manager only)."""

    serializer_class = UpdateInwardOtherMaterialSerializer

    @extend_schema(
        summary="Update an inward other-material lot (no writable fields)",
        request=UpdateInwardOtherMaterialSerializer,
        responses={200: InwardOtherMaterialPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        entry = get_object_or_404(
            InwardOtherMaterial.objects.select_related("return_order__order"),
            public_id=public_id,
        )
        # A lot an accepted return booked is owned by that return.
        entry.refuse_return_lot_change()

        serializer = UpdateInwardOtherMaterialSerializer(
            instance=entry, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        return Response(inward_other_material_payload(entry))

    @extend_schema(
        summary="Delete an inward other-material lot",
        responses={204: None},
    )
    def delete(self, request: Request, public_id: str) -> Response:
        entry = get_object_or_404(InwardOtherMaterial.objects.all(), public_id=public_id)
        entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
