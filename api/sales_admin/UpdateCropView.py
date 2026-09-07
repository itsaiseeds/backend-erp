"""Crop update/delete endpoint: ``PATCH``/``DELETE`` ``/api/sales-admin/crops/<id>``.

Only an application Admin may update or delete a crop (``admin_required`` on
``AdminApiView``). ``name`` is validated for uniqueness, excluding the crop
being edited. Soft-deleted crops are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import Crop
from api.admin import AdminApiView
from common.models.timestamped import indian_now

from .CropsView import CropPayloadSerializer


class UpdateCropSerializer(serializers.Serializer):
    """Request validation for updating a ``Crop`` (name only)."""

    name = serializers.CharField(
        max_length=255,
        required=False,
        error_messages={"blank": "Crop name may not be blank."},
    )

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("name may not be blank.")
        own_crop_id = self.instance.id if self.instance is not None else None
        qs = Crop.all_objects.filter(name=name)
        if own_crop_id is not None:
            qs = qs.exclude(id=own_crop_id)
        if qs.exists():
            raise serializers.ValidationError("A crop with this name already exists.")
        return name


class UpdateCropView(AdminApiView):
    """Update or delete a single crop (app admin only)."""

    serializer_class = UpdateCropSerializer
    admin_required = True

    @extend_schema(
        summary="Update a crop",
        request=UpdateCropSerializer,
        responses={200: CropPayloadSerializer},
    )
    def patch(self, request, id: int):
        crop = get_object_or_404(Crop.objects.all(), pk=id)

        serializer = UpdateCropSerializer(instance=crop, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if "name" in serializer.validated_data:
            crop.name = serializer.validated_data["name"]
            crop.save()

        return Response({"id": crop.id, "name": crop.name})

    @extend_schema(
        summary="Delete a crop",
        responses={204: None},
    )
    def delete(self, request, id: int):
        crop = get_object_or_404(Crop.objects.all(), pk=id)
        crop.is_deleted = True
        crop.deleted_at = indian_now()
        crop.deleted_by = request.user
        crop.save(
            update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
