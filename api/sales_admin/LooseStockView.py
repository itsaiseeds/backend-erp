"""Loose-stock position endpoint: ``GET`` ``/api/sales-admin/loose-stock``.

Only an application Admin may view it (``admin_required``). Returns every
counted loose pool -- one line per ``(product, packet_weight)`` -- with the
reserved, consumed and available figures derived from custom-order status.

``snapshot_date`` is the date the loose count was last taken, and is ``null``
when no loose count has ever been recorded. It is deliberately independent of
the daily bag snapshot: the loose count is optional, so it may be older than
today and still be the truth.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator import InventoryOperations
from api.admin import AdminApiView
from api.sales_admin.UpdateLooseStockView import LooseStockProductRefSerializer


class LooseStockLineSerializer(serializers.Serializer):
    """Output shape for one loose pool's position."""

    product = LooseStockProductRefSerializer()
    packet_weight = serializers.DecimalField(max_digits=8, decimal_places=3)
    on_hand = serializers.IntegerField()
    reserved = serializers.IntegerField()
    consumed = serializers.IntegerField()
    available = serializers.IntegerField()


class LooseStockPositionSerializer(serializers.Serializer):
    """Output shape for the whole loose position."""

    snapshot_date = serializers.DateField(allow_null=True)
    lines = LooseStockLineSerializer(many=True)


def loose_line_payload(entry: dict) -> dict:
    """Response shape for one ``loose_stock_position`` entry."""
    product = entry["product"]
    return {
        "product": {
            "public_id": product.public_id,
            "name": product.name,
        },
        "packet_weight": str(entry["packet_weight"]),
        "on_hand": entry["packets_on_hand"],
        "reserved": entry["packets_reserved"],
        "consumed": entry["packets_consumed"],
        "available": entry["packets_available"],
    }


class LooseStockView(AdminApiView):
    """Read the current loose-stock position for every counted pool."""

    admin_required = True

    @extend_schema(
        summary="Read the loose-stock position",
        responses={200: LooseStockPositionSerializer},
    )
    def get(self, request):
        snapshot_date = InventoryOperations.latest_loose_snapshot_date()
        return Response(
            {
                "snapshot_date": snapshot_date.isoformat() if snapshot_date else None,
                "lines": [
                    loose_line_payload(entry)
                    for entry in InventoryOperations.loose_stock_position()
                ],
            }
        )
