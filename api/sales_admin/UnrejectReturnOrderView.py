"""Unreject endpoint: ``POST /api/sales-admin/unreject-return-order/<public_id>``.

Brings a REJECTED return back to PENDING. A rejected return did not count toward
its order's limit, and another return may have been raised since, so the order
must still be DISPATCHED or DELIVERED with no other live return, and the items
must still fit what the challan carried; a breach is a 400.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import ReturnOrder
from aggregator.ReturnOrderOperations import unreject_return_order
from api.return_order_serializers import ReturnOrderPayloadSerializer

from .ReturnOrderTransitionView import RETURN_PUBLIC_ID_PARAMETER, ReturnOrderTransitionView


class UnrejectReturnOrderView(ReturnOrderTransitionView):
    """Undo a rejection, returning the return to PENDING."""

    @extend_schema(
        summary="Unreject a return (REJECTED -> PENDING)",
        request=None,
        parameters=[RETURN_PUBLIC_ID_PARAMETER],
        responses={200: ReturnOrderPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, ret: ReturnOrder, request: Request) -> None:
        unreject_return_order(ret, admin=request.user)
