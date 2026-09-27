"""Revert dispatch: ``POST /api/sales-admin/revert-custom-order-dispatch/<public_id>``.

Reverses ``dispatch-custom-order``: a DISPATCHED custom order goes back to
CONFIRMED, and its loose packets move back from consumed to reserved on their
own, since both figures are derived from the status. Any
``actual_delivery_date`` is cleared.

The dispatch record and the challan stay attached -- a re-dispatch overwrites
them -- and the challan list stops showing it, because it filters on status.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import revert_dispatch
from aggregator.models import CustomOrder
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CustomOrderTransitionView import CustomOrderTransitionView
from .CustomOrderView import CUSTOM_ORDER_PUBLIC_ID_PARAMETER


class RevertCustomOrderDispatchView(CustomOrderTransitionView):
    """Undo a custom order's dispatch, returning it to CONFIRMED."""

    @extend_schema(
        summary="Revert a custom order's dispatch (DISPATCHED -> CONFIRMED)",
        request=None,
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={200: CustomOrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: CustomOrder, request: Request) -> None:
        revert_dispatch(order)
