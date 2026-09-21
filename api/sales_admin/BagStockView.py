"""Bag-stock position endpoint: ``GET`` ``/api/sales-admin/bag-stock``.

Only an application Admin may view it (``admin_required``). Returns every
counted sealed-bag line -- one per active packaging -- with the reserved,
consumed and available bag figures derived from order status.

``snapshot_date`` is the date the bag count was last taken, and is ``null``
when no bag count has ever been recorded. It is the most recent bag snapshot:
recording today's bag count purges older rows, so that date is the truth.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator import InventoryOperations
from api.admin import AdminApiView
from api.sales_admin.UpdateBagStockView import PackagingRefSerializer


class BagStockLineSerializer(serializers.Serializer):
    """Output shape for one packaging's bag position."""

    packaging = PackagingRefSerializer()
    on_hand = serializers.IntegerField()
    reserved = serializers.IntegerField()
    consumed = serializers.IntegerField()
    available = serializers.IntegerField()


class BagStockPositionSerializer(serializers.Serializer):
    """Output shape for the whole bag position."""

    snapshot_date = serializers.DateField(allow_null=True)
    lines = BagStockLineSerializer(many=True)


def bag_line_payload(entry: dict) -> dict:
    """Response shape for one ``stock_position`` entry."""
    packaging = entry["packaging"]
    return {
        "packaging": {
            "public_id": packaging.public_id,
            "product": {
                "public_id": packaging.product.public_id,
                "name": packaging.product.name,
            },
            "packet_weight": str(packaging.packet_weight),
            "packets": packaging.packets,
        },
        "on_hand": entry["packets_on_hand"],
        "reserved": entry["packets_reserved"],
        "consumed": entry["packets_consumed"],
        "available": entry["packets_available"],
    }


class BagStockView(AdminApiView):
    """Read the current bag-stock position for every counted packaging."""

    admin_required = True

    @extend_schema(
        summary="Read the bag-stock position",
        responses={200: BagStockPositionSerializer},
    )
    def get(self, request):
        snapshot_date = InventoryOperations.latest_snapshot_date()
        return Response(
            {
                "snapshot_date": snapshot_date.isoformat() if snapshot_date else None,
                "lines": [
                    bag_line_payload(entry)
                    for entry in InventoryOperations.stock_position(snapshot_date)
                ],
            }
        )
