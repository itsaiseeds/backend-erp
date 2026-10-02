"""Dispatch endpoint: ``POST /api/sales-admin/dispatch-custom-order/<public_id>``.

The custom-order counterpart of ``dispatch-order``: a sales admin records that a
CONFIRMED custom order has left the warehouse. The request carries the same
four journey fields -- where it left from, and who drove it in what -- plus a
lot number per line.

**A custom order always goes on our own vehicle.** It has no transport agency,
so the dispatch is recorded against ``PrivateDispatchDetails`` and there is no
LR number to record for it later.

That also makes the driver and vehicle **required** here, even though the shared
``DispatchOrderSerializer`` accepts them blank -- they are optional only on an
agency dispatch, and a custom order never is. The rule is enforced by
``OrderOperations.assert_driver_details``, called unconditionally from
``dispatch_custom_order``.

The date is today and the destination the custom order's own delivery city,
exactly as for an order.

``items`` names every line once, keyed by ``product_public_id`` plus
``packet_weight`` -- the pair ``GET /custom-order/<public_id>`` hands back for
each line. Which lines those are is checked against the custom order itself, in
``DispatchOperations``.
"""

from __future__ import annotations

from decimal import Decimal

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import dispatch_custom_order
from aggregator.models import CustomOrder
from aggregator.OrderOperations import OWN_VEHICLE_FIELD_REQUIRED
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CustomOrderTransitionView import CustomOrderTransitionView
from .CustomOrderView import CUSTOM_ORDER_PUBLIC_ID_PARAMETER
from .DispatchOrderView import DispatchOrderSerializer


class CustomDispatchItemLotSerializer(serializers.Serializer):
    """The lot number for one loose line of the custom order being dispatched."""

    product_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "product_public_id is required.",
            "required": "product_public_id is required.",
        },
    )
    packet_weight = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        min_value=Decimal("0.001"),
        error_messages={"required": "packet_weight is required."},
    )
    lot_number = serializers.CharField(
        max_length=64,
        error_messages={
            "blank": "lot_number is required.",
            "required": "lot_number is required.",
        },
    )


def _own_vehicle_field(field: str, **kwargs) -> serializers.CharField:
    """One driver/vehicle field, declared as an own-vehicle dispatch needs it.

    ``dispatch_custom_order`` enforces this anyway (every caller goes through
    ``assert_driver_details``), but re-declaring it here is what makes the
    generated schema tell the truth: a client reading ``openapi.yml`` would
    otherwise be told these are optional, which they are only on an *agency*
    dispatch -- and a custom order never is one.
    """
    message = OWN_VEHICLE_FIELD_REQUIRED.format(field=field)
    return serializers.CharField(
        error_messages={"required": message, "blank": message}, **kwargs
    )


class DispatchCustomOrderSerializer(DispatchOrderSerializer):
    """``dispatch-order``'s request, with lot numbers keyed by loose line.

    The driver and vehicle are required again here -- see
    :func:`_own_vehicle_field`.
    """

    driver_name = _own_vehicle_field("driver_name", max_length=255)
    driver_number = _own_vehicle_field("driver_number", max_length=10)
    vehicle_number = _own_vehicle_field("vehicle_number", max_length=32)

    items = CustomDispatchItemLotSerializer(
        many=True,
        allow_empty=False,
        error_messages={"required": "items is required."},
        help_text="One lot number per line of the custom order; every line must appear.",
    )

    def validate_items(self, value: list[dict]) -> list[dict]:
        keys = [(item["product_public_id"], item["packet_weight"]) for item in value]
        if len(set(keys)) != len(keys):
            raise serializers.ValidationError(
                "The same product and packet weight is listed twice."
            )
        return value


class DispatchCustomOrderView(CustomOrderTransitionView):
    """Record an own-vehicle dispatch against a CONFIRMED custom order (app admin only)."""

    serializer_class = DispatchCustomOrderSerializer

    @extend_schema(
        summary="Dispatch a custom order (always own vehicle)",
        request=DispatchCustomOrderSerializer,
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={200: CustomOrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: CustomOrder, request: Request) -> None:
        serializer = DispatchCustomOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        dispatch_custom_order(
            order,
            actor=request.user,
            from_city=data["from_city_id"],
            driver_name=data["driver_name"],
            driver_number=data["driver_number"],
            vehicle_number=data["vehicle_number"],
            lot_numbers={
                (item["product_public_id"], item["packet_weight"]): item["lot_number"]
                for item in data["items"]
            },
        )
