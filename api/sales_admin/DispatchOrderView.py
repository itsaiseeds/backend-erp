"""Dispatch endpoint: ``POST /api/sales-admin/dispatch-order/<public_id>``.

A sales admin records that a verified order has left the warehouse. **Only a
CONFIRMED order can be dispatched**: an unverified order has not been checked
against stock, so shipping it would consume bags nobody confirmed were there.

**Which kind of dispatch this is comes from the order, not from the request.**
An order carrying a ``transport_agency`` goes by that carrier; one without it
goes on our own vehicle. That is the same rule ``dispatch_mode`` reports on every
order payload, so what was planned at booking time is what gets recorded -- and
the caller cannot contradict it.

* **agency** (the order has a transport agency) -- ``lr_number`` is *optional*.
  The transporter usually issues the consignment note after collection, so a
  dispatch is recorded while it is still pending and the number is filled in
  later through ``edit-order``.
* **private** (the order has none) -- ``vehicle_number`` and ``driver_number``
  are both required.

Both kinds take ``dispatch_date``, ``from_city_id`` and ``to_city_id``. Fields
belonging to the other kind are rejected rather than ignored, so a request that
misunderstands which kind of dispatch it is fails loudly.

The details are written and the status moved in one transaction, and the order's
bags shift from reserved to consumed on their own -- both figures are derived
from its status, never stored.
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

    The kind of dispatch is read off the order in ``context["order"]`` -- it is
    whether that order has a ``transport_agency`` -- so this serializer only
    checks that the body matches the kind, never decides it.
    """

    dispatch_date = serializers.DateField(
        error_messages={"required": "dispatch_date is required."}
    )
    from_city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        error_messages={"required": "from_city_id is required."},
    )
    to_city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        error_messages={"required": "to_city_id is required."},
    )
    lr_number = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        help_text=(
            "Agency dispatches only, and optional even then: leave it out while "
            "the transporter's consignment note is still pending."
        ),
    )
    vehicle_number = serializers.CharField(max_length=32, required=False)
    driver_number = serializers.CharField(
        max_length=10, required=False, validators=[validate_phone_number]
    )

    def validate(self, attrs):
        order = self.context["order"]
        private_fields = ("vehicle_number", "driver_number")

        if order.transport_agency_id:
            sent = [field for field in private_fields if field in attrs]
            if sent:
                raise serializers.ValidationError(
                    f"This order is dispatched by {order.transport_agency.name}, "
                    f"so {' and '.join(sent)} do not apply. Send lr_number, or "
                    "nothing while it is still pending."
                )
        else:
            if "lr_number" in attrs:
                raise serializers.ValidationError(
                    "This order has no transport agency, so it is a private "
                    "dispatch and carries no LR number. Send vehicle_number and "
                    "driver_number instead."
                )
            missing = [field for field in private_fields if not attrs.get(field)]
            if missing:
                raise serializers.ValidationError(
                    f"A private dispatch needs {' and '.join(missing)}."
                )
        return attrs


class DispatchOrderView(OrderTransitionView):
    """Record a dispatch against a verified order (app admin only)."""

    serializer_class = DispatchOrderSerializer

    @extend_schema(
        summary="Dispatch a verified order (by agency or own vehicle)",
        request=DispatchOrderSerializer,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        serializer = DispatchOrderSerializer(
            data=request.data, context={"order": order}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        dispatch_order(
            order,
            actor=request.user,
            dispatch_date=data["dispatch_date"],
            from_city=data["from_city_id"],
            to_city=data["to_city_id"],
            lr_number=data.get("lr_number", ""),
            vehicle_number=data.get("vehicle_number", ""),
            driver_number=data.get("driver_number", ""),
        )
