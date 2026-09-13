"""Hold endpoint: ``POST /api/sales-admin/hold-order/<public_id>``.

Parks an order that cannot proceed yet -- a payment query, a stock delay, a
client asking to pause. Allowed from BOOKED, UNDER_REVIEW and CONFIRMED, but not
once the order has been dispatched: the goods have left, so the status must keep
saying so.

Holding a CONFIRMED order **releases its reserved bags**, which is the point:
reservations are derived from the status, so the stock a paused order was
holding returns to the available pool with no bookkeeping.

ON_HOLD is verifiable, so a held order resumes through ``verify-order``.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Order
from aggregator.OrderOperations import hold_order
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class HoldOrderView(OrderTransitionView):
    """Put an order on hold, releasing any stock it reserved."""

    @extend_schema(
        summary="Put an order on hold",
        request=None,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        hold_order(order)
