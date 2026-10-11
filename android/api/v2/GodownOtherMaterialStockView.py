"""Godown other-material stock: ``GET`` ``/android/api/v2/godown/other-material-stock``.

v1 plus ``?group_by=configuration``: one line per ``(product, packet weight,
material type)`` -- each carrying ``product`` and ``packet_weight`` -- instead
of one per material type, as ``api.sales_admin.OtherMaterialStockView`` does.
Without ``group_by`` the response is exactly v1's. Godown-manager token only.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InwardOperations
from android.api.base import AndroidGodownBaseView
from api.inward_serializers import OtherMaterialStockSerializer
from common.views.paginated_date_range import parse_int


class GodownOtherMaterialStockView(AndroidGodownBaseView):
    """Read the other-material on-hand position (godown manager only)."""

    @extend_schema(
        summary="Other-material on-hand stock, per material type or per configuration",
        parameters=[
            OpenApiParameter(
                "group_by",
                str,
                enum=["configuration"],
                required=False,
                description="``configuration`` groups by product, packet weight and material type.",
            )
        ],
        responses={200: OtherMaterialStockSerializer},
    )
    def get(self, request: Request) -> Response:
        raw = request.query_params.get("material_type")
        material_type_ids = [parse_int(part) for part in raw.split(",")] if raw else None
        return Response(
            InwardOperations.other_material_stock_payload(
                material_type_ids,
                by_configuration=request.query_params.get("group_by") == "configuration",
            )
        )
