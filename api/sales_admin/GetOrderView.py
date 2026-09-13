"""Order detail endpoint: ``GET /api/sales-admin/order/<public_id>``.

One order in full: its own fields, every line with the bag it names and that
line's price, and the **whole** client -- every address and every transport
agency, each with its link id, so the edit screen's pickers need no second call.

Soft-deleted and unknown orders are never found (404).

``order_detail_queryset`` is exported and reused by every other sales-admin
order endpoint, the way ``ProductsView.products_queryset`` is reused by
``UpdateProductView``: the joins a full order payload needs are declared once.
"""

from __future__ import annotations

from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import ClientAddress, ClientTransportAgency, Order, OrderItem
from aggregator.OrderOperations import order_detail_payload
from api.admin import AdminApiView
from api.order_serializers import OrderDetailPayloadSerializer

ORDER_PUBLIC_ID_PARAMETER = OpenApiParameter(
    "public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The order's public id, e.g. ORD-E79QA0E2OIHF.",
)


def order_detail_queryset() -> QuerySet:
    """The fully joined single-order queryset behind every detail payload.

    ``client_payload`` walks the client's three link tables and each address's
    geography, so those are prefetched here rather than left to fire one query
    per row at render time.
    """
    return Order.objects.select_related(
        "status",
        "created_by",
        "verified_by",
        "transport_agency",
        "client__status",
        "client__created_by",
        "client__verified_by",
        "delivery_address__city",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=OrderItem.objects.select_related("product_packaging__product"),
        ),
        Prefetch(
            "client__client_addresses",
            queryset=ClientAddress.objects.select_related(
                "address__pincode",
                "address__city",
                "address__state",
                "address__country",
            ),
        ),
        "client__client_contacts__contact",
        Prefetch(
            "client__client_transport_agencies",
            queryset=ClientTransportAgency.objects.select_related("transport_agency"),
        ),
    )


class GetOrderView(AdminApiView):
    """Get one order in full, by ``public_id`` (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Get an order in full (order + items + the client's full details)",
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def get(self, request: Request, public_id: str) -> Response:
        order = get_object_or_404(order_detail_queryset(), public_id=public_id)
        return Response(order_detail_payload(order))
