"""Revert dispatch: ``POST /api/sales-admin/revert-dispatch/<public_id>``.

Reverses ``dispatch-order``: a dispatched order goes back to CONFIRMED, and its
bags move back from consumed to reserved on their own, since both figures are
derived from the status.

The dispatch record stays attached. It is what actually happened, and a
re-dispatch overwrites it -- only the status is rewound. Any
``actual_delivery_date`` is cleared, because the order has not been delivered.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Order
from aggregator.OrderOperations import revert_dispatch
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class RevertDispatchView(OrderTransitionView):
    """Undo a dispatch, returning the order to CONFIRMED."""

    @extend_schema(
        summary="Revert a dispatch (DISPATCHED -> CONFIRMED)",
        request=None,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        revert_dispatch(order)
