"""Other-material stock endpoint: ``GET`` ``/api/sales-admin/other-material-stock``.

Read-time, aggregate, never stored: the on-hand position of every material type,
computed on the fly as the ``InwardOtherMaterial`` lots received minus what the
packets currently packed have used per their ``OtherMaterialRecipe`` (the same
derivation raw material uses -- see ``InventoryOperations.other_material_used``).
A negative figure means more packets were counted than the recorded lots cover.

Other material needs no lab gate, so a lot counts once its ``effective_date``
has come -- ``effective_date <= today`` -- and is no longer soft-deleted.
Tomorrow's dated stock is not on-hand yet. The unit of each ``on_hand`` figure
is the material type's own ``unit_type`` (count / kg / litre).

Optional ``?material_type=<id,...>`` narrows the report to those types.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InwardOperations
from api.admin import AdminApiView
from api.inward_serializers import OtherMaterialStockSerializer
from common.views.paginated_date_range import parse_int


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
        by_configuration = request.query_params.get("group_by") == "configuration"
        lines = (
            InwardOperations.other_material_on_hand_by_configuration(
                as_of, material_type_ids=material_type_ids
            )
            if by_configuration
            else InwardOperations.other_material_on_hand(as_of, material_type_ids=material_type_ids)
        )
        return Response(
            {
                "as_of": as_of.isoformat(),
                "lines": [
                    {
                        **(
                            {
                                "product": {
                                    "public_id": line["product_public_id"],
                                    "name": line["product_name"],
                                },
                                "packet_weight": str(line["packet_weight"]),
                            }
                            if by_configuration
                            else {}
                        ),
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
