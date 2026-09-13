"""Dispatch endpoint: ``POST /api/sales-admin/dispatch-order/<public_id>``.

A sales admin records that a verified order has left the warehouse. **Only a
CONFIRMED order can be dispatched**: an unverified order has not been checked
against stock, so shipping it would consume bags nobody confirmed were there.

The request is the same four fields whichever kind of dispatch it is: where it
left from, and who drove it in what.

**Which kind it is comes from the order, not the request.** An order carrying a
``transport_agency`` is recorded against ``DispatchDetails``; one without it
against ``PrivateDispatchDetails``. That is the same rule ``dispatch_mode``
reports on every order payload, so what was planned at booking time is what gets
recorded -- and the caller cannot contradict it.

Two fields are derived rather than accepted: the dispatch **date** is today,
because the dispatch is being recorded as it happens, and the **destination**
city is the order's own delivery address, which is where the goods are going by
definition. ``from_city_id`` is still an input until there is a warehouse to
default it from.

The transporter's ``lr_number`` is not accepted here -- it is issued after
collection, so every agency dispatch starts with it blank.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import City, Order
from aggregator.OrderOperations import dispatch_order
from api.order_serializers import OrderDetailPayloadSerializer
from authentication.validators import validate_phone_number

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class DispatchOrderSerializer(serializers.Serializer):
    """Request validation for recording a dispatch.

    Every field is required. There is no per-kind branching: an agency dispatch
    and an own-vehicle one carry exactly the same details, and which table they
    land in is the order's business, not the request's.
    """

    from_city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        error_messages={"required": "from_city_id is required."},
        help_text="Where the goods left from. An input until a warehouse can default it.",
    )
    driver_name = serializers.CharField(
        max_length=255,
        error_messages={
            "required": "driver_name is required.",
            "blank": "driver_name is required.",
        },
    )
    driver_number = serializers.CharField(
        max_length=10,
        validators=[validate_phone_number],
        error_messages={
            "required": "driver_number is required.",
            "blank": "driver_number is required.",
        },
    )
    vehicle_number = serializers.CharField(
        max_length=32,
        error_messages={
            "required": "vehicle_number is required.",
            "blank": "vehicle_number is required.",
        },
    )


class DispatchOrderView(OrderTransitionView):
    """Record a dispatch against a verified order (app admin only)."""

    serializer_class = DispatchOrderSerializer

    @extend_schema(
        summary="Dispatch a verified order",
        request=DispatchOrderSerializer,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        serializer = DispatchOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        dispatch_order(
            order,
            actor=request.user,
            from_city=data["from_city_id"],
            driver_name=data["driver_name"],
            driver_number=data["driver_number"],
            vehicle_number=data["vehicle_number"],
        )
