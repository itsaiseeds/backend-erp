"""Custom-order detail endpoint: ``/api/sales-admin/custom-order/<public_id>``.

``GET`` returns one custom order in full: its own fields, every loose-packet
line with its price, and the **whole** client -- every address with its link id,
so the edit screen's address picker needs no second call.

``DELETE`` soft deletes it, but only while it is CONFIRMED: once dispatched the
packets have left, and the order is history. Its reserved packets go back to
the loose pool on their own. 204 on success.

Any sales admin may read or delete any custom order -- not only the ones they
booked. Soft-deleted and unknown custom orders are never found (404).

``custom_order_detail_queryset`` and ``get_locked_custom_order`` are exported
and reused by ``edit-custom-order`` and ``create-custom-order``, the way
``GetOrderView.order_detail_queryset`` is reused across the order endpoints.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Prefetch, QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import (
    custom_order_detail_payload,
    delete_custom_order,
)
from aggregator.models import ClientAddress, ClientTransportAgency, CustomOrder, CustomOrderItem
from api.admin import AdminApiView
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

CUSTOM_ORDER_PUBLIC_ID_PARAMETER = OpenApiParameter(
    "public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The custom order's public id, e.g. CORD-E79QA0E2OIHF.",
)


def custom_order_detail_queryset() -> QuerySet:
    """The fully joined single-custom-order queryset behind every detail payload.

    ``client_payload`` walks the client's three link tables and each address's
    geography, so those are prefetched here rather than left to fire one query
    per row at render time.
    """
    return CustomOrder.objects.select_related(
        "status",
        "created_by",
        "verified_by",
        "client__status",
        "client__created_by",
        "client__verified_by",
        "delivery_address__city",
        "booked_for__address__pincode",
        "booked_for__address__city",
        "booked_for__address__state",
        "booked_for__address__country",
        "booked_for",
    ).prefetch_related(
        Prefetch("items", queryset=CustomOrderItem.objects.select_related("product")),
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


def get_locked_custom_order(public_id: str) -> CustomOrder:
    """Lock the custom order row ``FOR UPDATE``, then load it in full.

    Two queries on purpose, for the reason ``GetOrderView.get_locked_order``
    gives: the lock is taken on the bare row so a waiter re-checks no joins,
    and the detail load then reads the committed state the guard must see.

    Must be called inside ``transaction.atomic``.
    """
    pk = (
        CustomOrder.objects.select_for_update()
        .filter(public_id=public_id)
        .values_list("pk", flat=True)
        .first()
    )
    if pk is None:
        raise Http404("No CustomOrder matches the given query.")
    return custom_order_detail_queryset().get(pk=pk)


class CustomOrderView(AdminApiView):
    """Get (GET) or delete (DELETE) one custom order (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Get a custom order in full (order + items + the client's full details)",
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={200: CustomOrderDetailPayloadSerializer},
    )
    def get(self, request: Request, public_id: str) -> Response:
        order = get_object_or_404(custom_order_detail_queryset(), public_id=public_id)
        return Response(custom_order_detail_payload(order))

    @extend_schema(
        summary="Delete a custom order that has not been dispatched (CONFIRMED)",
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={204: None},
    )
    def delete(self, request: Request, public_id: str) -> Response:
        # Locked, so a concurrent edit cannot write lines onto an order that
        # is being withdrawn between the guard and the delete.
        with transaction.atomic():
            order = get_locked_custom_order(public_id)
            delete_custom_order(order, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
