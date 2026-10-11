"""Order edit endpoint: ``PATCH /android/api/v1/edit-order/<public_id>``.

A sales person corrects an order they booked **while it is still BOOKED** (the
office has not verified it yet). Once it is verified, held, rejected or
dispatched, only a sales admin can change it. An order that is not the caller's
reads as unknown (404) -- it is not hinted to exist.

Editable: ``items`` (a bag and a quantity, at the bag's list price -- a sales
person does not negotiate, so no price may be sent), ``client_address_id``,
``client_transport_agency_id``, ``expected_delivery_date``, ``special_comments``
(appended, never replacing) and ``booked_for``. The client cannot change.

Every field is optional and only what is sent is applied; ``items``, when sent,
is a full replacement, as on ``api/sales-admin/edit-order``. The address and
agency are *link* ids scoped to the order's own client.

An admin with app access may edit on behalf of a sales person by sending
``created_by`` (their user id); the order must be that person's.
"""

from __future__ import annotations

from django.db import transaction
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ClientChildOrgOperations import resolve_child_org
from aggregator.OrderOperations import (
    ORDER_CORE_FIELDS,
    SALESPERSON_EDITABLE_STATUS_CODES,
    assert_order_status,
    order_detail_payload,
    sync_order_items,
    update_order_core,
)
from android.api.base import AndroidBaseView
from android.api.sales_person_scope import resolve_sales_person
from api.order_serializers import OrderDetailPayloadSerializer
from api.sales_admin.GetOrderView import ORDER_PUBLIC_ID_PARAMETER, get_locked_order
from api.sales_admin.UpdateOrderView import UpdateOrderSerializer


class SalesPersonOrderItemWriteSerializer(serializers.Serializer):
    """One desired line: a bag and how many -- always at the bag's list price."""

    product_packaging_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "product_packaging_public_id is required.",
            "required": "product_packaging_public_id is required.",
        },
    )
    quantity = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "quantity is required.",
            "min_value": "Quantity must be at least 1.",
        },
    )


class EditOrderSerializer(UpdateOrderSerializer):
    """The admin edit request without prices or an actual delivery date."""

    actual_delivery_date = None
    items = SalesPersonOrderItemWriteSerializer(many=True, required=False)
    created_by = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Admin only: user id of the sales person whose order this is.",
    )


class EditOrderView(AndroidBaseView):
    """Edit one of the caller's BOOKED orders."""

    serializer_class = EditOrderSerializer

    @extend_schema(
        summary="Edit a BOOKED order (sales person)",
        request=EditOrderSerializer,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        sales_person = resolve_sales_person(request, request.data.get("created_by"))
        with transaction.atomic():
            order = get_locked_order(public_id)
            if order.created_by_id != sales_person.id:
                raise Http404("No Order matches the given query.")
            assert_order_status(order, SALESPERSON_EDITABLE_STATUS_CODES, "edit")

            serializer = EditOrderSerializer(data=request.data, context={"order": order})
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            if "booked_for" in data:
                data["booked_for"] = (
                    resolve_child_org(order.client, data["booked_for"], sales_person)
                    if data["booked_for"] is not None
                    else None
                )

            core = {field: data[field] for field in ORDER_CORE_FIELDS if field in data}
            if core:
                update_order_core(order, **core)
            if "items" in data:
                sync_order_items(order, data["resolved_items"], sales_person)

        order.refresh_from_db()
        return Response(order_detail_payload(order))
