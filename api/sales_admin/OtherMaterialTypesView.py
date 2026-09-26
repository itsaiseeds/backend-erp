"""Other-material-type master-data endpoint: ``GET``/``POST``.

Path: ``/api/sales-admin/other-material-types``.

Only an application Admin may view or create material types (``admin_required``
on ``AdminApiView``). Soft-deleted types are never returned. Like ``Party``,
a type is a lookup row addressed by its primary key. The three reference rows
(``bag_outer_cover``, ``packet_outer_cover``, ``leaflets``) are seeded by
``dml.sql``.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.InwardOperations import other_material_type_payload
from aggregator.models import OtherMaterialType, OtherMaterialUnitType
from api.admin import AdminApiView


class OtherMaterialTypePayloadSerializer(serializers.Serializer):
    """Output shape for one material-type row."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_type = serializers.CharField()


class CreateOtherMaterialTypeSerializer(serializers.Serializer):
    """Request validation for creating a new ``OtherMaterialType``."""

    name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Material type name is required.",
            "required": "Material type name is required.",
        },
    )
    unit_type = serializers.ChoiceField(
        choices=OtherMaterialUnitType.choices,
        error_messages={"required": "Unit type is required."},
    )

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Material type name may not be blank.")
        if OtherMaterialType.all_objects.filter(name=name).exists():
            raise serializers.ValidationError(
                "A material type with this name already exists."
            )
        return name


class OtherMaterialTypesView(AdminApiView):
    """List (GET) or create (POST) other material types (app admin only)."""

    serializer_class = CreateOtherMaterialTypeSerializer
    admin_required = True

    @extend_schema(
        summary="List other material types",
        responses={200: OtherMaterialTypePayloadSerializer(many=True)},
    )
    def get(self, request):
        types = OtherMaterialType.objects.order_by("name")
        return Response([other_material_type_payload(t) for t in types])

    @extend_schema(
        summary="Create an other material type",
        request=CreateOtherMaterialTypeSerializer,
        responses={201: OtherMaterialTypePayloadSerializer},
    )
    def post(self, request):
        serializer = CreateOtherMaterialTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        material_type = OtherMaterialType.objects.create(
            name=data["name"], unit_type=data["unit_type"], created_by=request.user
        )
        return Response(
            other_material_type_payload(material_type),
            status=status.HTTP_201_CREATED,
        )
