"""Godown other-material stock: ``GET`` ``/android/api/v1/godown/other-material-stock``.

The Android counterpart of ``api.sales_admin.OtherMaterialStockView`` (same
derivation, same ``?material_type=`` narrowing); godown-manager token only.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InwardOperations
from android.api.base import AndroidGodownBaseView
from api.inward_serializers import OtherMaterialStockSerializer
from common.views.paginated_date_range import parse_int


class GodownOtherMaterialStockView(AndroidGodownBaseView):
    """Read the other-material on-hand position (godown manager only)."""

    @extend_schema(
        summary="Other-material on-hand stock, per material type",
        responses={200: OtherMaterialStockSerializer},
    )
    def get(self, request: Request) -> Response:
        raw = request.query_params.get("material_type")
        material_type_ids = [parse_int(part) for part in raw.split(",")] if raw else None
        as_of = InwardOperations.today()
        lines = InwardOperations.other_material_on_hand(as_of, material_type_ids=material_type_ids)
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
