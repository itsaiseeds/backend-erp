"""Revert-accept endpoint: ``POST /api/sales-admin/revert-accept-return-order/<public_id>``.

Undoes an accept: the inward raw and packing-material lots it booked are removed
and the return goes back to PENDING (so it can be edited, accepted again or
rejected). It is the **only** way those lots are ever removed -- the normal
inward edit and delete paths refuse them.

Refused (400, nothing changes) when removing the raw kilograms or the packing
material would take their available stock below zero, i.e. it has since been
packed or used. This is the same guard that protects deleting an in-use lot.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import ReturnOrder
from aggregator.ReturnOrderOperations import revert_accept_return_order
from api.return_order_serializers import ReturnOrderPayloadSerializer

from .ReturnOrderTransitionView import RETURN_PUBLIC_ID_PARAMETER, ReturnOrderTransitionView


class RevertAcceptReturnOrderView(ReturnOrderTransitionView):
    """Undo an accept, removing the stock it booked."""

    @extend_schema(
        summary="Revert an accepted return (ACCEPTED -> PENDING), removing its inward stock",
        request=None,
        parameters=[RETURN_PUBLIC_ID_PARAMETER],
        responses={200: ReturnOrderPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, ret: ReturnOrder, request: Request) -> None:
        revert_accept_return_order(ret, admin=request.user)
