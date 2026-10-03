"""Godown raw-material stock: ``GET`` ``/android/api/v1/godown/raw-material-stock``.

The Android counterpart of ``api.sales_admin.RawMaterialStockView`` (same
derivation, same ``?product=`` narrowing); godown-manager token only.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InwardOperations
from android.api.base import AndroidGodownBaseView
from api.inward_serializers import RawMaterialStockSerializer
from common.views.paginated_date_range import parse_str


class GodownRawMaterialStockView(AndroidGodownBaseView):
    """Read the incoming raw-material position (godown manager only)."""

    @extend_schema(
        summary="Raw-material incoming stock, per product",
        responses={200: RawMaterialStockSerializer},
    )
    def get(self, request: Request) -> Response:
        product_filter = request.query_params.get("product")
        product_public_ids = parse_str(product_filter).split(",") if product_filter else None
        as_of = InwardOperations.today()
        lines = [
            {
                "product": line["public_id"],
                "name": line["name"],
                "is_usable": line["is_usable"],
                "incoming_kg": str(line["incoming_kg"]),
                "packed_kg": str(line["packed_kg"]),
                "wasted_kg": str(line["wasted_kg"]),
                "available_kg": str(line["available_kg"]),
                "rejected_kg": str(line["rejected_kg"]),
            }
            for line in InwardOperations.raw_incoming_stock(
                as_of, product_public_ids=product_public_ids
            )
        ]
        return Response({"as_of": as_of.isoformat(), "lines": lines})
