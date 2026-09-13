"""Unverify endpoint: ``POST /api/sales-admin/unverify-order/<public_id>``.

Reverses ``verify-order``: a confirmed order goes back to UNDER_REVIEW and its
``verified_by`` / ``verified_at`` are cleared, because it is no longer approved.

The bags it was holding are released automatically -- reservations are derived
from the order's status, never stored.

UNDER_REVIEW is itself verifiable, so this is a round trip rather than a dead
end: an admin can pull an order back, correct it through ``edit-order`` (which a
confirmed order also allows, but whose stock implications are only re-checked at
verification), and approve it again.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Order
from aggregator.OrderOperations import unverify_order
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class UnverifyOrderView(OrderTransitionView):
    """Withdraw an order's approval, returning it to UNDER_REVIEW."""

    @extend_schema(
        summary="Unverify an order (CONFIRMED -> UNDER_REVIEW)",
        request=None,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        unverify_order(order)
