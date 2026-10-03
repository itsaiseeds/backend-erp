"""Return order endpoint: ``GET`` / ``POST /android/api/v1/return-order/<order_public_id>``.

A client sends goods back against an order that was already shipped, and the
sales person who booked that order records it here. Scoped to the caller: the
order is looked up with ``created_by=request.user``, so another sales person's
order reads as unknown (404).

* ``GET`` is the prefill the return screen opens with: a summary of the order,
  its live return (if any), and one line per product / packet weight on the
  challan -- the packets dispatched, the packets still returnable and a suggested
  price per packet (the order line's bag price divided by the packets in the bag).
* ``POST`` raises a PENDING return. Only a DISPATCHED or DELIVERED order can have
  one, an order may have only one live (PENDING or ACCEPTED) return, and nothing
  may be returned beyond what the challan carried; a breach is a 400 and nothing
  is written. Accepting or rejecting it is the sales admin's call.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Order
from aggregator.ReturnOrderOperations import (
    create_return_order,
    return_order_payload,
    return_order_prefill_payload,
)
from android.api.base import AndroidBaseView
from api.return_order_serializers import (
    ReturnOrderPayloadSerializer,
    ReturnOrderPrefillSerializer,
    ReturnOrderWriteSerializer,
)

ORDER_PUBLIC_ID_PARAMETER = OpenApiParameter(
    "order_public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The order's public id, e.g. ORD-E79QA0E2OIHF.",
)


class ReturnOrderView(AndroidBaseView):
    """Prefill (GET) or raise (POST) a return against one of the caller's orders."""

    serializer_class = ReturnOrderWriteSerializer

    def _order(self, request: Request, order_public_id: str) -> Order:
        return get_object_or_404(
            Order.objects.select_related("status", "client"),
            public_id=order_public_id,
            created_by=request.user,
        )

    @extend_schema(
        operation_id="android_api_v1_return_order_prefill",
        summary="Prefill a return: the order's challan lines and what is still returnable",
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: ReturnOrderPrefillSerializer},
    )
    def get(self, request: Request, order_public_id: str) -> Response:
        order = self._order(request, order_public_id)
        return Response(return_order_prefill_payload(order))

    @extend_schema(
        operation_id="android_api_v1_return_order_create",
        summary="Raise a return against a dispatched order",
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
        )
        return Response(return_order_payload(ret), status=status.HTTP_201_CREATED)
