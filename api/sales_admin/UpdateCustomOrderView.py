"""Custom-order update endpoint: ``PATCH /api/sales-admin/edit-custom-order/<public_id>``.

A sales admin corrects a custom order: its delivery address, its dates, its
comments and its lines -- adding, removing, re-pricing and re-counting them in
one call. Any sales admin may edit any custom order, not only the ones they
booked.

The rules are ``edit-order``'s:

* **The client cannot be changed**, and the address is named by *link* id
  scoped to the order's own client, so a foreign one cannot be attached.
* **The audit record and the status are not fields here.** Who booked and
  confirmed the order is not rewritten by an edit screen; a ``status`` or
  ``client`` key is ignored like any other unknown field.
* ``special_comments`` **accumulates**: whatever is sent is appended as a new
  line.
* ``items``, when sent, is a **full declarative replacement**: a line left out
  is removed. A line is keyed by ``(product_public_id, packet_weight)``.

**Only a CONFIRMED custom order is editable** -- once dispatched the packets
have left. And because a CONFIRMED custom order's packets are reserved,
raising a count or adding a line must be covered by the loose pool (the packets
it already holds count towards it); a shortfall is a 400 and nothing is written.
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import (
    CUSTOM_ORDER_CORE_FIELDS,
    EDITABLE_CUSTOM_ORDER_STATUS_CODES,
    assert_custom_order_status,
    custom_order_detail_payload,
    sync_custom_order_items,
    update_custom_order_core,
)
from aggregator.models import ClientAddress
from api.admin import AdminApiView
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CreateCustomOrderView import (
    CustomOrderItemWriteSerializer,
    resolve_custom_order_items,
    validate_custom_order_item_list,
)
from .CustomOrderView import (
    CUSTOM_ORDER_PUBLIC_ID_PARAMETER,
    custom_order_detail_queryset,
    get_locked_custom_order,
)


class UpdateCustomOrderSerializer(serializers.Serializer):
    """Request validation for an admin's custom-order update -- every field optional.

    No field may declare a ``default``: the view applies a field only when the
    key is present in ``validated_data``, and DRF injects a declared default
    even for an absent key, which would silently rewrite an untouched column.
    """

    client_address_id = serializers.IntegerField(
        required=False,
        help_text="A ClientAddress link id belonging to the custom order's client.",
    )
    expected_delivery_date = serializers.DateField(required=False)
    actual_delivery_date = serializers.DateField(required=False, allow_null=True)
    special_comments = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=(
            "A remark to add to the custom order. Appended as a new line -- it "
            "never replaces what is already there."
        ),
    )
    items = CustomOrderItemWriteSerializer(many=True, required=False)

    def validate_items(self, value: list[dict]) -> list[dict]:
        return validate_custom_order_item_list(value)

    def validate(self, attrs: dict) -> dict:
        order = self.context["order"]

        if "client_address_id" in attrs:
            link = (
                ClientAddress.objects.filter(
                    client=order.client, id=attrs["client_address_id"]
                )
                .select_related("address")
                .first()
            )
            if link is None:
                raise serializers.ValidationError(
                    {"client_address_id": "No such address for this client."}
                )
            attrs["delivery_address"] = link.address

        if "items" in attrs:
            attrs["resolved_items"] = resolve_custom_order_items(attrs["items"], order)

        return attrs


class UpdateCustomOrderView(AdminApiView):
    """Update a custom order, including its lines (app admin only)."""

    serializer_class = UpdateCustomOrderSerializer
    admin_required = True

    @extend_schema(
        summary="Update a custom order (including its items)",
        request=UpdateCustomOrderSerializer,
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={200: CustomOrderDetailPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        # Locked for the whole edit, so a concurrent delete or dispatch cannot
        # move the order out of an editable status between the guard and the
        # write.
        with transaction.atomic():
            order = get_locked_custom_order(public_id)
            assert_custom_order_status(order, EDITABLE_CUSTOM_ORDER_STATUS_CODES, "edit")

            serializer = UpdateCustomOrderSerializer(
                data=request.data, context={"order": order}
            )
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            core = {
                field: data[field] for field in CUSTOM_ORDER_CORE_FIELDS if field in data
            }
            if core:
                update_custom_order_core(order, **core)
            if "items" in data:
                sync_custom_order_items(order, data["resolved_items"], request.user)

        # Re-read in full: the prefetched lines are stale once rewritten.
        order = custom_order_detail_queryset().get(pk=order.pk)
        return Response(custom_order_detail_payload(order))
