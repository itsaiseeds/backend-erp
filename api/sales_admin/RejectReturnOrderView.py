"""Reject endpoint: ``POST /api/sales-admin/reject-return-order/<public_id>``.

Turns a PENDING return down. No stock moves, so no ledger row is written. Only a
PENDING return can be rejected: an ACCEPTED one must be reverted first
(``revert-accept-return-order``). A rejected return keeps its order link but is
hidden from the order's details and does not count toward its returnable limit;
``unreject-return-order`` brings it back.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import ReturnOrder
from aggregator.ReturnOrderOperations import reject_return_order
from api.return_order_serializers import ReturnOrderPayloadSerializer

from .ReturnOrderTransitionView import RETURN_PUBLIC_ID_PARAMETER, ReturnOrderTransitionView


class RejectReturnOrderView(ReturnOrderTransitionView):
    """Reject a pending return."""

    @extend_schema(
        summary="Reject a return (PENDING -> REJECTED)",
        request=None,
        parameters=[RETURN_PUBLIC_ID_PARAMETER],
        responses={200: ReturnOrderPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, ret: ReturnOrder, request: Request) -> None:
        reject_return_order(ret, admin=request.user)
