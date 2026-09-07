"""Crop master-data endpoint: ``GET``/``POST`` ``/api/sales-admin/crops``.

Only an application Admin may view or create crops (``admin_required`` on
``AdminApiView``, the session-only web base). Soft-deleted crops are never
returned.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import Crop
from api.admin import AdminApiView


class CropPayloadSerializer(serializers.Serializer):
    """Output shape for one crop row."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class CreateCropSerializer(serializers.Serializer):
    """Request validation for creating a new ``Crop``."""

    name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Crop name is required.",
            "required": "Crop name is required.",
        },
    )

    def validate_name(self, value):
        name = value.strip()
        if Crop.all_objects.filter(name=name).exists():
            raise serializers.ValidationError("A crop with this name already exists.")
        return name


class CropsView(AdminApiView):
    """List (GET) or create (POST) crops (app admin only)."""

    serializer_class = CreateCropSerializer
    admin_required = True

    @extend_schema(
        summary="List crops",
        responses={200: CropPayloadSerializer(many=True)},
    )
    def get(self, request):
        crops = Crop.objects.order_by("name")
        return Response([{"id": crop.id, "name": crop.name} for crop in crops])

    @extend_schema(
        summary="Create a crop",
        request=CreateCropSerializer,
        responses={201: CropPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateCropSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        crop = Crop.objects.create(
            name=serializer.validated_data["name"], created_by=request.user
        )
        return Response(
            {"id": crop.id, "name": crop.name},
            status=status.HTTP_201_CREATED,
        )
