"""Mark delivered: ``POST /api/sales-admin/mark-custom-order-delivered/<public_id>``.

Delivers a DISPATCHED custom, waste or rejected order (always own vehicle, so
there is never an LR). Delivery is dated today. No stock figure moves:
DISPATCHED and DELIVERED both count as consumed.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import mark_delivered
from aggregator.models import CustomOrder
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CustomOrderTransitionView import CustomOrderTransitionView
from .CustomOrderView import CUSTOM_ORDER_PUBLIC_ID_PARAMETER


class MarkCustomOrderDeliveredView(CustomOrderTransitionView):
    """Deliver a custom, waste or rejected order (app admin only)."""

    @extend_schema(
        summary="Mark a custom / waste / rejected order delivered (DISPATCHED -> DELIVERED)",
        request=None,
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={200: CustomOrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: CustomOrder, request: Request) -> None:
        mark_delivered(order)
