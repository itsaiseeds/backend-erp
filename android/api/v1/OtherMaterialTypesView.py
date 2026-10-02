"""Utility endpoint: every other-material type, ``GET .../utilities/other-material-types``.

Path: ``/android/api/v1/utilities/other-material-types``.

The flat, unpaginated material-type picker (rows built with
``InwardOperations.other_material_type_payload``). Token-only; open to either
Android role. Soft-deleted types are excluded.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import other_material_type_payload
from aggregator.models import OtherMaterialType
from android.api.base import AndroidSharedView


class UtilityOtherMaterialTypeSerializer(serializers.Serializer):
    """Output shape for one material type row (schema only)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_type = serializers.CharField(help_text="Count / kg / litre.")


class OtherMaterialTypesView(AndroidSharedView):
    """List every other-material type."""

    @extend_schema(
        summary="List every other-material type (not paginated)",
        responses={200: UtilityOtherMaterialTypeSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        material_types = OtherMaterialType.objects.order_by("name", "id")
        return Response([other_material_type_payload(item) for item in material_types])
