"""Order update endpoint: ``PATCH /api/sales-admin/edit-order/<public_id>``.

A sales admin corrects an order: its delivery address, its transport agency, its
dates, its comments, its status, and its lines -- adding, removing, re-pricing
and re-quantifying them in one call.

**The client cannot be changed.** An order belongs to the client it was booked
for; moving it would invalidate its delivery address, its transport agency and
the prices its lines were negotiated at. There is no client field on the
serializer, and the address and agency are named by *link* id scoped to the
order's own client, so a foreign one cannot be attached either. A request
carrying a client key is simply ignored, like any other unknown field.

``verified_by`` / ``verified_at`` / ``created_by`` / ``created_at`` are not
fields here at all. They are the audit record: who booked the order and who
approved it is not something an edit screen rewrites, and approval has its own
endpoint (``verify-order``).

``special_comments`` **accumulates**: whatever is sent is appended as a new
line, so an admin adding a remark can never erase one somebody left earlier.

**A dispatched order is frozen.** Once the goods have left, the order is history
-- every edit is rejected, not merely the ones touching its lines.

Every field is optional and only what is sent is applied. ``items``, when sent,
is a **full declarative replacement**, the same contract the client's address /
contact / agency lists use on ``update-client/``: the admin sends the list they
want, and a line they leave out is removed.

The address and the agency arrive as *link* ids, so each resolves with a single
lookup scoped to the client -- an id belonging to somebody else simply does not
match, and the "belongs to this client" rule ``Order.clean()`` enforces is
satisfied by construction.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import ClientAddress, ClientTransportAgency, ProductPackaging
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import (
    EDITABLE_STATUS_CODES,
    ORDER_CORE_FIELDS,
    assert_order_status,
    order_detail_payload,
    sync_order_items,
    update_order_core,
)
from api.admin import AdminApiView
from api.order_serializers import OrderDetailPayloadSerializer

from .GetOrdersView import ORDER_STATUS_CODES
from .GetOrderView import ORDER_PUBLIC_ID_PARAMETER, order_detail_queryset

# Upper bound on distinct bags in one order -- an editing screen, not a bulk import.
MAX_ORDER_ITEMS = 100


class OrderItemWriteSerializer(serializers.Serializer):
    """One desired line of the order: a bag, how many, and optionally at what price."""

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
    negotiated_selling_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        help_text=(
            "Whole-bag rate for this line. Omit it to leave an existing line's "
            "price alone, or to charge a new line the bag's list price."
        ),
    )


class UpdateOrderSerializer(serializers.Serializer):
    """Request validation for an admin's order update -- every field optional.

    No field may declare a ``default``: the view applies a field only when the
    key is present in ``validated_data``, and DRF injects a declared default
    even for an absent key, which would silently rewrite an untouched column.
    """

    client_address_id = serializers.IntegerField(
        required=False,
        help_text="A ClientAddress link id belonging to the order's client.",
    )
    client_transport_agency_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=(
            "A ClientTransportAgency link id belonging to the order's client; "
            "send null for a private (own-vehicle) dispatch."
        ),
    )
    expected_delivery_date = serializers.DateField(required=False)
    actual_delivery_date = serializers.DateField(required=False, allow_null=True)
    special_comments = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=(
            "A remark to add to the order. Appended as a new line -- it never "
            "replaces what is already there."
        ),
    )
    status = serializers.ChoiceField(choices=ORDER_STATUS_CODES, required=False)
    items = OrderItemWriteSerializer(many=True, required=False)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("An order must keep at least one item.")
        if len(value) > MAX_ORDER_ITEMS:
            raise serializers.ValidationError(
                f"An order can hold at most {MAX_ORDER_ITEMS} items."
            )
        public_ids = [item["product_packaging_public_id"] for item in value]
        if len(set(public_ids)) != len(public_ids):
            raise serializers.ValidationError(
                "The same product packaging is listed twice."
            )
        return value

    def validate(self, attrs):
        order = self.context["order"]

        if "client_address_id" in attrs:
            link = ClientAddress.objects.filter(
                client=order.client, id=attrs["client_address_id"]
            ).select_related("address").first()
            if link is None:
                raise serializers.ValidationError(
                    {"client_address_id": "No such address for this client."}
                )
            attrs["delivery_address"] = link.address

        if "client_transport_agency_id" in attrs:
            agency_id = attrs["client_transport_agency_id"]
            if agency_id is None:
                attrs["transport_agency"] = None
            else:
                link = ClientTransportAgency.objects.filter(
                    client=order.client, id=agency_id
                ).select_related("transport_agency").first()
                if link is None:
                    raise serializers.ValidationError(
                        {
                            "client_transport_agency_id": (
                                "No such transport agency for this client."
                            )
                        }
                    )
                attrs["transport_agency"] = link.transport_agency

        if "items" in attrs:
            attrs["resolved_items"] = self._resolve_items(attrs["items"])

        return attrs

    def _resolve_items(self, items: list[dict]) -> list[dict]:
        """Turn the submitted lines into the shape ``sync_order_items`` takes.

        One query for every bag named, so an unknown public id is reported as a
        list rather than one id at a time.
        """
        public_ids = [item["product_packaging_public_id"] for item in items]
        packagings = {
            packaging.public_id: packaging
            for packaging in ProductPackaging.objects.filter(public_id__in=public_ids)
        }
        missing = [pid for pid in public_ids if pid not in packagings]
        if missing:
            raise serializers.ValidationError(
                {"items": f"Unknown product packaging: {', '.join(missing)}."}
            )
        return [
            {
                "product_packaging": packagings[item["product_packaging_public_id"]],
                "quantity": item["quantity"],
                "negotiated_selling_price": item.get("negotiated_selling_price"),
            }
            for item in items
        ]


class UpdateOrderView(AdminApiView):
    """Update an order, including its lines (app admin only)."""

    serializer_class = UpdateOrderSerializer
    admin_required = True

    @extend_schema(
        summary="Update an order (including its items)",
        request=UpdateOrderSerializer,
        parameters=[ORDER_PUBLIC_ID_PARAMETER],
        responses={200: OrderDetailPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        order = get_object_or_404(order_detail_queryset(), public_id=public_id)
        assert_order_status(order, EDITABLE_STATUS_CODES, "edit")

        serializer = UpdateOrderSerializer(
            data=request.data, context={"order": order}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            core = {field: data[field] for field in ORDER_CORE_FIELDS if field in data}
            if "status" in data:
                core["status"] = StatusIds[data["status"]]
            if core:
                update_order_core(order, **core)
            if "items" in data:
                sync_order_items(order, data["resolved_items"], request.user)

        # The prefetched lines are stale once they have been rewritten;
        # refresh_from_db drops the prefetch cache so the response re-reads.
        order.refresh_from_db()
        return Response(order_detail_payload(order))
