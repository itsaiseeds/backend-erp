"""Other-material-type update/delete endpoint: ``PATCH``/``DELETE``.

Path: ``/api/sales-admin/other-material-types/<id>``.

Only an application Admin may update or delete a material type. Soft-deleted
types are never found (404). ``name`` is validated for uniqueness, excluding the
type being edited.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.InwardOperations import other_material_type_payload
from aggregator.models import OtherMaterialType, OtherMaterialUnitType
from api.admin import AdminApiView

from .OtherMaterialTypesView import OtherMaterialTypePayloadSerializer


class UpdateOtherMaterialTypeSerializer(serializers.Serializer):
    """Request validation for updating an ``OtherMaterialType`` (all fields optional)."""

    name = serializers.CharField(
        max_length=255,
        required=False,
        error_messages={"blank": "Material type name may not be blank."},
    )
    unit_type = serializers.ChoiceField(
        choices=OtherMaterialUnitType.choices, required=False
    )

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Material type name may not be blank.")
        qs = OtherMaterialType.all_objects.filter(name=name)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A material type with this name already exists."
            )
        return name


class UpdateOtherMaterialTypeView(AdminApiView):
    """Update or delete a single other material type (app admin only)."""

    serializer_class = UpdateOtherMaterialTypeSerializer
    admin_required = True

    @extend_schema(
        summary="Update an other material type",
        request=UpdateOtherMaterialTypeSerializer,
        responses={200: OtherMaterialTypePayloadSerializer},
    )
    def patch(self, request, id: int):
        material_type = get_object_or_404(OtherMaterialType.objects.all(), pk=id)

        serializer = UpdateOtherMaterialTypeSerializer(
            instance=material_type, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        for field in ("name", "unit_type"):
            if field in serializer.validated_data:
                setattr(material_type, field, serializer.validated_data[field])
        material_type.save()
        return Response(other_material_type_payload(material_type))

    @extend_schema(
        summary="Delete an other material type",
        responses={204: None},
    )
    def delete(self, request, id: int):
        material_type = get_object_or_404(OtherMaterialType.objects.all(), pk=id)
        material_type.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
