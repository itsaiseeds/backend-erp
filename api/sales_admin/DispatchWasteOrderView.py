"""Dispatch endpoint: ``POST /api/sales-admin/dispatch-waste-order/<public_id>``.

``dispatch-custom-order`` for a waste order: a sales admin records that a
CONFIRMED waste order has left the warehouse. It always goes on our own vehicle,
so the driver and vehicle are required, the date is today and the destination
the delivery address's city.

Unlike a packet order, **lot numbers are optional**: waste has no production
batch. ``items`` may name some lines (keyed by ``product_public_id``) to record
a lot against them; a line left out is dispatched with a blank lot, and the
whole ``items`` list may be omitted.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import dispatch_waste_order
from aggregator.models import CustomOrder
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CustomOrderTransitionView import CustomOrderTransitionView
from .CustomOrderView import CUSTOM_ORDER_PUBLIC_ID_PARAMETER
from .DispatchCustomOrderView import _own_vehicle_field
from .DispatchOrderView import DispatchOrderSerializer


class WasteDispatchItemLotSerializer(serializers.Serializer):
    """The (optional) lot number for one line of the waste order being dispatched."""

    product_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "product_public_id is required.",
            "required": "product_public_id is required.",
        },
    )
    lot_number = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        default="",
    )


class DispatchWasteOrderSerializer(DispatchOrderSerializer):
    """``dispatch-order``'s request, with the driver and vehicle required and optional lots."""

    driver_name = _own_vehicle_field("driver_name", max_length=255)
    driver_number = _own_vehicle_field("driver_number", max_length=10)
    vehicle_number = _own_vehicle_field("vehicle_number", max_length=32)

    items = WasteDispatchItemLotSerializer(
        many=True,
        required=False,
        help_text="Optional lot numbers, one entry per product at most.",
    )

    def validate_items(self, value: list[dict]) -> list[dict]:
        ids = [item["product_public_id"] for item in value]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("The same product is listed twice.")
        return value


class DispatchWasteOrderView(CustomOrderTransitionView):
    """Record an own-vehicle dispatch against a CONFIRMED waste order (app admin only)."""

    serializer_class = DispatchWasteOrderSerializer

    @extend_schema(
        summary="Dispatch a waste order (always own vehicle)",
        request=DispatchWasteOrderSerializer,
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={200: CustomOrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: CustomOrder, request: Request) -> None:
        serializer = DispatchWasteOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        dispatch_waste_order(
            order,
            actor=request.user,
            from_city=data["from_city_id"],
            driver_name=data["driver_name"],
            driver_number=data["driver_number"],
            vehicle_number=data["vehicle_number"],
            lot_numbers={
                item["product_public_id"]: item["lot_number"]
                for item in data.get("items", [])
                if item["lot_number"]
            },
        )
