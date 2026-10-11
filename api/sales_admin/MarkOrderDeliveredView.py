"""Mark delivered: ``POST /api/sales-admin/mark-order-delivered/<public_id>``.

For a DISPATCHED order that went on our own vehicle, where no transporter will
ever issue an LR number. Delivery is dated today. An agency order is refused:
recording its LR number (``upload-lr-number``) delivers it.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Order
from aggregator.OrderOperations import mark_private_order_delivered
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class MarkOrderDeliveredView(OrderTransitionView):
    """Deliver an own-vehicle order (app admin only)."""

    @extend_schema(
        summary="Mark an own-vehicle order delivered (DISPATCHED -> DELIVERED)",
        request=None,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        mark_private_order_delivered(order, actor=request.user)
