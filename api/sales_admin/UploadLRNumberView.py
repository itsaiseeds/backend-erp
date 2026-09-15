"""LR endpoint: ``POST /api/sales-admin/upload-lr-number/<public_id>``.

A sales admin records the transporter's consignment note against an order that
has already been dispatched. It is a separate call from ``dispatch-order`` for
the reason ``DispatchDetails.lr_number`` is nullable in the first place: the
carrier issues the LR *after* collecting the goods, so it cannot be known at the
moment the dispatch is recorded.

**A private dispatch has no LR number**, and this endpoint says so with a 400
rather than accepting one. The number identifies a third party's consignment;
when the goods went on our own vehicle there is no third party and no
consignment note, so a value here would be a fiction the challan then printed.

Re-dispatching an order (revert, dispatch again) starts a new journey on a new
``DispatchDetails`` row, so the LR must be recorded again -- the old note
described the old journey.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.DispatchOperations import set_lr_number
from aggregator.models import Order
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER
from .OrderTransitionView import OrderTransitionView


class UploadLRNumberSerializer(serializers.Serializer):
    """Request validation for recording an LR number."""

    lr_number = serializers.CharField(
        max_length=64,
        trim_whitespace=True,
        error_messages={
            "required": "lr_number is required.",
            "blank": "lr_number is required.",
        },
        help_text="The transporter's consignment note number.",
    )


class UploadLRNumberView(OrderTransitionView):
    """Record the transporter's LR against a dispatched order (app admin only)."""

    serializer_class = UploadLRNumberSerializer

    @extend_schema(
        summary="Record the LR number of an agency dispatch",
        request=UploadLRNumberSerializer,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return self.transition(request, public_id)

    def apply_transition(self, order: Order, request: Request) -> None:
        serializer = UploadLRNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        set_lr_number(order, lr_number=serializer.validated_data["lr_number"])
