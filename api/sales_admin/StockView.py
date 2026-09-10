"""Stock-position endpoint: ``GET`` ``/api/sales-admin/get-stock/<public_id>``.

Only an application Admin may view it (``admin_required``). The same route
serves both pools: a ``PP-…`` public id returns the **sealed-bag** position of
one packaging (the unit ``OrderItem.quantity`` is counted in), while a ``P-…``
public id returns the **loose-packet** position of one product (the unit
``CustomOrderItem.packets`` is counted in).

Reserved and consumed figures are derived from order / custom-order status,
never stored, so the numbers always reflect the current state of the books.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.models import Product, ProductPackaging
from api.admin import AdminApiView


class StockPayloadSerializer(serializers.Serializer):
    """Output shape for a stock position (bag or loose-packet line)."""

    public_id = serializers.CharField()
    name = serializers.CharField(required=False)
    snapshot_date = serializers.DateField()
    on_hand = serializers.IntegerField(min_value=0)
    reserved = serializers.IntegerField(min_value=0)
    consumed = serializers.IntegerField(min_value=0)
    available = serializers.IntegerField(min_value=0)


class StockView(AdminApiView):
    """Read the current stock position for a packaging or product."""

    admin_required = True

    @extend_schema(
        summary="Read the stock position for a packaging or product",
        responses={200: StockPayloadSerializer},
    )
    def get(self, request, public_id):
        snapshot_date = (
            InventoryOperations.latest_snapshot_date()
            or InventoryOperations.today()
        )

        if public_id.startswith("PP-"):
            packaging = ProductPackaging.objects.filter(public_id=public_id).first()
            if packaging is None:
                raise NotFound("Unknown product packaging.")
            return Response(
                {
                    "public_id": packaging.public_id,
                    "name": (
                        f"{packaging.product.name}: "
                        f"{packaging.packets} × {packaging.packet_weight}kg"
                    ),
                    "snapshot_date": snapshot_date.isoformat(),
                    "on_hand": InventoryOperations.on_hand_bags(
                        packaging, snapshot_date
                    ),
                    "reserved": InventoryOperations.reserved_bags(packaging),
                    "consumed": InventoryOperations.consumed_bags(
                        packaging, snapshot_date
                    ),
                    "available": InventoryOperations.available_bags(
                        packaging, snapshot_date
                    ),
                }
            )

        if public_id.startswith("P-"):
            product = Product.objects.filter(public_id=public_id).first()
            if product is None:
                raise NotFound("Unknown product.")
            return Response(
                {
                    "public_id": product.public_id,
                    "name": product.name,
                    "snapshot_date": snapshot_date.isoformat(),
                    "on_hand": InventoryOperations.on_hand_loose_packets(
                        product, snapshot_date
                    ),
                    "reserved": InventoryOperations.reserved_loose_packets(product),
                    "consumed": InventoryOperations.consumed_loose_packets(
                        product, snapshot_date
                    ),
                    "available": InventoryOperations.available_loose_packets(
                        product, snapshot_date
                    ),
                }
            )

        raise NotFound("Unknown stock id.")
