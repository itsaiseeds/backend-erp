"""Stock-position endpoint: ``GET`` ``/api/sales-admin/get-stock/<public_id>``.

Only an application Admin may view it (``admin_required``). The same route
serves both pools: a ``PP-…`` public id returns the **sealed-bag** position of
one packaging (the unit ``OrderItem.quantity`` is counted in), while a ``P-…``
public id returns that product's **loose-packet** position (the unit
``CustomOrderItem.packets`` is counted in).

The loose response is broken down **per packet weight**, because a loose pool
is identified by ``(product, packet_weight)``: a product packed as both
1kg x 20 and 1kg x 30 has one pool of loose 1kg packets. Summing those weights
into a single product figure would add 1kg packets to 500g packets, so the
breakdown is the only honest shape.

Reserved and consumed figures are derived from order / custom-order status,
never stored, so the numbers always reflect the current state of the books.
"""

from __future__ import annotations

from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema
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
    on_hand = serializers.IntegerField()
    reserved = serializers.IntegerField()
    consumed = serializers.IntegerField()
    available = serializers.IntegerField()


class ProductLooseWeightLineSerializer(serializers.Serializer):
    """Output shape for one packet-weight line of a product's loose position."""

    packet_weight = serializers.DecimalField(max_digits=8, decimal_places=3)
    on_hand = serializers.IntegerField()
    reserved = serializers.IntegerField()
    consumed = serializers.IntegerField()
    available = serializers.IntegerField()


class ProductLooseStockPayloadSerializer(serializers.Serializer):
    """Output shape for a product's loose position, one line per packet weight."""

    public_id = serializers.CharField()
    name = serializers.CharField()
    snapshot_date = serializers.DateField()
    lines = ProductLooseWeightLineSerializer(many=True)


class StockView(AdminApiView):
    """Read the current stock position for a packaging or product."""

    admin_required = True

    @extend_schema(
        summary="Read the stock position for a packaging or product",
        description=(
            "A ``PP-…`` id returns the sealed-bag position of one packaging. A "
            "``P-…`` id returns that product's loose position, one line per "
            "packet weight."
        ),
        responses={
            200: PolymorphicProxySerializer(
                component_name="StockPosition",
                serializers=[StockPayloadSerializer, ProductLooseStockPayloadSerializer],
                resource_type_field_name=None,
            )
        },
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
            # Loose stock lives on its own date: the count is optional, so the
            # latest loose date may well be older than the bag snapshot above.
            loose_date = InventoryOperations.loose_date()
            return Response(
                {
                    "public_id": product.public_id,
                    "name": product.name,
                    "snapshot_date": loose_date.isoformat(),
                    "lines": [
                        {
                            "packet_weight": str(weight),
                            "on_hand": InventoryOperations.on_hand_loose_packets(
                                product, weight, loose_date
                            ),
                            "reserved": InventoryOperations.reserved_loose_packets(
                                product, weight
                            ),
                            "consumed": InventoryOperations.consumed_loose_packets(
                                product, weight, loose_date
                            ),
                            "available": InventoryOperations.available_loose_packets(
                                product, weight, loose_date
                            ),
                        }
                        for weight in InventoryOperations.product_loose_weights(product)
                    ],
                }
            )

        raise NotFound("Unknown stock id.")
