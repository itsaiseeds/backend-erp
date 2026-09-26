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
collection, so every agency dispatch starts with it blank. It is recorded later
by ``POST /api/sales-admin/upload-lr-number/<public_id>``.

``items`` is the one addition to the four: a **lot number per line**, keyed by
``product_packaging_public_id`` (the id ``GET /order/<public_id>`` hands back for
each line). It must name every line of the order exactly once -- the dispatch
writes the order's challan, and a challan that cannot say which batch a bag came
from is not a challan. Which packaging is which is checked against the order
itself, in ``DispatchOperations``.
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


class DispatchItemLotSerializer(serializers.Serializer):
    """The lot number for one line of the order being dispatched."""

    product_packaging_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "product_packaging_public_id is required.",
            "required": "product_packaging_public_id is required.",
        },
    )
    lot_number = serializers.CharField(
        max_length=64,
        error_messages={
            "blank": "lot_number is required.",
            "required": "lot_number is required.",
        },
    )


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
    items = DispatchItemLotSerializer(
        many=True,
        allow_empty=False,
        error_messages={"required": "items is required."},
        help_text="One lot number per line of the order; every line must appear.",
    )

    def validate_items(self, value):
        """Reject a packaging listed twice -- one lot number per line, no more.

        Whether the list *covers* the order is not checked here: that needs the
        order, which the serializer does not have. ``dispatch_order`` does it.
        """
        public_ids = [item["product_packaging_public_id"] for item in value]
        if len(set(public_ids)) != len(public_ids):
            raise serializers.ValidationError(
                "The same product packaging is listed twice."
            )
        return value


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
            lot_numbers={
                item["product_packaging_public_id"]: item["lot_number"]
                for item in data["items"]
            },
        )
