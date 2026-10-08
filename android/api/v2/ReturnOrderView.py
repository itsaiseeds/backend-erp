"""Return order endpoint, v2: ``GET`` / ``POST /android/api/v2/return-order/<order_public_id>``.

Same as v1 except that an order may carry any number of returns
(``docs/prd/multiple-return-orders.md``):

* ``GET`` answers ``return_orders`` -- every live (PENDING or ACCEPTED) return,
  newest first -- instead of v1's single ``return_order``.
* ``POST`` raises another PENDING return as long as, with every other live
  return, it stays within what the challan carried per product / packet weight.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ReturnOrderOperations import (
    create_return_order,
    return_order_payload,
    return_order_prefill_payload,
)
from android.api.v1.ReturnOrderView import ORDER_PUBLIC_ID_PARAMETER
from android.api.v1.ReturnOrderView import ReturnOrderView as ReturnOrderViewV1
from api.return_order_serializers import (
    ReturnOrderPayloadSerializer,
    ReturnOrderPrefillV2Serializer,
    ReturnOrderWriteSerializer,
)


class ReturnOrderView(ReturnOrderViewV1):
    """Prefill (GET) or raise (POST) one of possibly many returns against an order."""

    @extend_schema(
        operation_id="android_api_v2_return_order_prefill",
        summary="Prefill a return: challan lines, what is returnable and every live return",
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: ReturnOrderPrefillV2Serializer},
    )
    def get(self, request: Request, order_public_id: str) -> Response:
        order = self._order(request, order_public_id)
        return Response(return_order_prefill_payload(order, many=True))

    @extend_schema(
        operation_id="android_api_v2_return_order_create",
        summary="Raise a return against a dispatched order (several allowed)",
        request=ReturnOrderWriteSerializer,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={201: ReturnOrderPayloadSerializer},
    )
    def post(self, request: Request, order_public_id: str) -> Response:
        order = self._order(request, order_public_id)
        serializer = ReturnOrderWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        ret = create_return_order(
            order,
            return_date=data.get("return_date"),
            items=data["resolved_items"],
            actor=request.user,
            single_live=False,
        )
        return Response(return_order_payload(ret), status=status.HTTP_201_CREATED)
