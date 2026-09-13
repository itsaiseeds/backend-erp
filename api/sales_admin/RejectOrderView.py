"""Reject endpoint: ``POST /api/sales-admin/reject-order/<public_id>``.

Turns an order down for good. Allowed from BOOKED, UNDER_REVIEW, CONFIRMED and
ON_HOLD, but not once the order has been dispatched -- goods that have shipped
cannot be un-ordered, and the status has to keep reflecting what happened.

**Rejection is terminal**: no verb moves an order out of REJECTED, and a
rejected order cannot be verified. Rejecting a CONFIRMED order releases the bags
it reserved, for the usual reason -- reservations are derived from the status.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Order
from aggregator.OrderOperations import reject_order
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class RejectOrderView(OrderTransitionView):
    """Reject an order for good, releasing any stock it reserved."""

    @extend_schema(
        summary="Reject an order (terminal)",
        request=None,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        reject_order(order)
