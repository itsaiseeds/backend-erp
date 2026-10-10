"""Godown raw-material waste row: PATCH/DELETE ``godown/raw-material-waste/<public_id>``.

The Android counterpart of ``api.sales_admin.UpdateRawMaterialWasteView``, with
the same rules. ``PATCH`` corrects ``quantity_kg`` and/or ``reason`` (the product
is fixed); raising the quantity beyond the product's unpacked raw kilograms is a
400, and so is lowering it below the waste a waste order already holds. ``DELETE``
(soft) removes a wrong entry, refused (400) when a waste order already holds
that waste. Soft-deleted rows are a 404. Godown-manager token only.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.InwardOperations import raw_waste_payload
from aggregator.models import RawMaterialWaste
from android.api.base import AndroidGodownBaseView
from api.inward_serializers import (
    RawMaterialWastePayloadSerializer,
    UpdateRawMaterialWasteSerializer,
)


class UpdateGodownRawMaterialWasteView(AndroidGodownBaseView):
    """Edit (PATCH) or soft-delete (DELETE) a raw-material waste row (godown manager only)."""

    serializer_class = UpdateRawMaterialWasteSerializer

    @extend_schema(
        summary="Edit a raw-material waste row (quantity / reason)",
        request=UpdateRawMaterialWasteSerializer,
        responses={200: RawMaterialWastePayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
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
    def delete(self, request: Request, public_id: str) -> Response:
        entry = get_object_or_404(RawMaterialWaste.objects.all(), public_id=public_id)
        entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
