"""Order verification endpoint: ``POST /api/sales-admin/verify-order/<public_id>``.

A sales admin approves an order against the warehouse count. The whole check and
the status change are one atomic transaction (``OrderOperations.verify_order``):
a shortfall on the last line leaves the order exactly as it was.

Three gates, all in the operations layer:

1. the order is BOOKED, UNDER_REVIEW or ON_HOLD -- a confirmed order cannot be
   confirmed twice, and a rejected one is terminal;
2. **today's** stock count is complete -- no count, no verification, so nothing
   is approved against figures nobody has checked;
3. every bag on the order has enough available stock, where available is the
   counted quantity minus what other confirmed orders already reserve.

An empty request body is expected; the order is named in the path.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Order
from aggregator.OrderOperations import verify_order
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class VerifyOrderView(OrderTransitionView):
    """Approve an order against stock availability (app admin only)."""

    @extend_schema(
        summary="Verify an order against today's stock count",
        request=None,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        if order.is_verified:
            raise serializers.ValidationError("This order is already verified.")
        verify_order(order, request.user)
