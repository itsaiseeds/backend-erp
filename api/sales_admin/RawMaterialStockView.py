"""Raw-material stock endpoint: ``GET`` ``/api/sales-admin/raw-material-stock``.

Read-time, aggregate, never stored: the incoming raw-material position of every
product, computed from ``InwardRawMaterial`` lots on the fly.

A lot counts toward the total only once it is **dated and usable** -- both an
``effective_date`` that has come ("tomorrow is not incoming yet") and
``status='in_use'`` (a ``lab_testing`` lot is held back until the lab signs
off). Soft-deleted lots never count.

Optional ``?product=<P-...,...>`` narrows the report to those products.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InwardOperations
from api.admin import AdminApiView
from common.views.paginated_date_range import parse_str


class RawMaterialStockLineSerializer(serializers.Serializer):
    """Output shape for one product's incoming position."""

    product = serializers.CharField(help_text="Product public id.")
    name = serializers.CharField(help_text="Product name.")
    incoming_kg = serializers.CharField(help_text="Sum of in-use KG with a reached effective date.")


class RawMaterialStockSerializer(serializers.Serializer):
    """Output shape for the whole incoming raw-material position."""

    as_of = serializers.DateField(help_text="The day the numbers are as of.")
    lines = RawMaterialStockLineSerializer(many=True)


class RawMaterialStockView(AdminApiView):
    """Read the incoming raw-material position (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Raw-material incoming stock, per product",
        responses={200: RawMaterialStockSerializer},
    )
    def get(self, request: Request):
        product_filter = request.query_params.get("product")
        product_public_ids = (
            parse_str(product_filter).split(",") if product_filter else None
        )
        as_of = InwardOperations.today()
        lines = [
            {
                "product": line["public_id"],
                "name": line["name"],
                "incoming_kg": str(line["incoming_kg"]),
            }
            for line in InwardOperations.raw_incoming_stock(
                as_of, product_public_ids=product_public_ids
            )
        ]
        return Response({"as_of": as_of.isoformat(), "lines": lines})
