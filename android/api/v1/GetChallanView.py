"""One of my dispatch challans: ``GET /android/api/v1/get-challan/<order_public_id>``.

The challan of a single order the calling sales person created -- the same
payload as one row of ``get-challans``. Scoped to the caller: another sales
person's order, an order that is not dispatched (or whose dispatch was
reverted), a custom order, or an unknown ``order_public_id`` is a 404, never a
403, so the response does not reveal that the order exists.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.DispatchOperations import challan_entry_payload
from android.api.base import AndroidBaseView
from api.sales_admin.GetDispatchChallansView import DispatchChallanItemSerializer

from .GetChallansView import owned_challan_queryset

_ORDER_PARAM = OpenApiParameter(
    "order_public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The order's public id, e.g. ORD-E79QA0E2OIHF.",
)


class GetChallanView(AndroidBaseView):
    """The challan of one of the caller's dispatched or delivered orders."""

    @extend_schema(
        summary="Get the dispatch challan of one of my orders",
        parameters=[_ORDER_PARAM],
        responses={200: DispatchChallanItemSerializer},
    )
    def get(self, request: Request, order_public_id: str) -> Response:
        entry = get_object_or_404(
            owned_challan_queryset(request.user), order__public_id=order_public_id
        )
        return Response(challan_entry_payload(entry))
