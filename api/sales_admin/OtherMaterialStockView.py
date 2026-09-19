"""Other-material stock endpoint: ``GET`` ``/api/sales-admin/other-material-stock``.

Read-time, aggregate, never stored: the on-hand position of every material type,
computed from ``InwardOtherMaterial`` lots on the fly.

Other material needs no lab gate, so a lot counts once its ``effective_date``
has come -- ``effective_date <= today`` -- and is no longer soft-deleted.
Tomorrow's dated stock is not on-hand yet. The unit of each ``on_hand`` figure
is the material type's own ``unit_type`` (count / kg / litre).

Optional ``?material_type=<id,...>`` narrows the report to those types.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InwardOperations
from api.admin import AdminApiView
from common.views.paginated_date_range import parse_int


class OtherMaterialTypeRefSerializer(serializers.Serializer):
    """Output shape for the ``material_type`` reference on a line."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_type = serializers.CharField(help_text="Count / kg / litre -- the unit of on_hand.")


class OtherMaterialStockLineSerializer(serializers.Serializer):
    """Output shape for one material type's on-hand position."""

    material_type = OtherMaterialTypeRefSerializer()
    on_hand = serializers.CharField(help_text="Sum of units with a reached effective date.")


class OtherMaterialStockSerializer(serializers.Serializer):
    """Output shape for the whole other-material position."""

    as_of = serializers.DateField(help_text="The day the numbers are as of.")
    lines = OtherMaterialStockLineSerializer(many=True)


class OtherMaterialStockView(AdminApiView):
    """Read the other-material on-hand position (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Other-material on-hand stock, per material type",
        responses={200: OtherMaterialStockSerializer},
    )
    def get(self, request: Request):
        raw = request.query_params.get("material_type")
        material_type_ids = (
            [parse_int(part) for part in raw.split(",")] if raw else None
        )
        as_of = InwardOperations.today()
        lines = InwardOperations.other_material_on_hand(
            as_of, material_type_ids=material_type_ids
        )
        return Response(
            {
                "as_of": as_of.isoformat(),
                "lines": [
                    {
                        "material_type": {
                            "id": line["material_type_id"],
                            "name": line["name"],
                            "unit_type": line["unit_type"],
                        },
                        "on_hand": str(line["on_hand"]),
                    }
                    for line in lines
                ],
            }
        )
