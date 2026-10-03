"""Serializers for the return-order endpoints.

Return payloads are built by hand in ``aggregator.ReturnOrderOperations``; the
output classes here exist so drf-spectacular can document the shape those
functions return, and the contract tests compare their keys with the payloads.
Shared between the Android app and the sales-admin website, as
``api.order_serializers`` is.

The input serializers resolve the request into the ``items`` shape the
operations take. Whether the items actually fit the order's challan is the
operations layer's call (``assert_items_within_limit``), so the rule holds
however a return is reached.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from aggregator.models import Product
from aggregator.ReturnOrderOperations import items_from_payload

# Upper bound on distinct lines in one return -- a screen, not a bulk import.
MAX_RETURN_ITEMS = 100


# -- Input --------------------------------------------------------------------


class ReturnOrderItemWriteSerializer(serializers.Serializer):
    """One returned line: a product's packets of one weight, and their price."""

    product_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "product_public_id is required.",
            "required": "product_public_id is required.",
        },
    )
    packet_weight = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        min_value=Decimal("0.001"),
        error_messages={"required": "packet_weight is required."},
        help_text="Weight of one returned packet, in kg (as on the challan).",
    )
    packets = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "packets is required.",
            "min_value": "packets must be at least 1.",
        },
    )
    price_per_packet = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        error_messages={"required": "price_per_packet is required."},
    )


class ReturnOrderWriteSerializer(serializers.Serializer):
    """Request body to raise (Android POST) or edit (admin PATCH) a return.

    ``items`` is a full declarative replacement on edit: a line left out is
    removed. ``return_date`` defaults to today on create and is informational
    only. No field declares a ``default``, so an absent key stays absent.
    """

    return_date = serializers.DateField(required=False)
    items = ReturnOrderItemWriteSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A return must have at least one item.")
        if len(value) > MAX_RETURN_ITEMS:
            raise serializers.ValidationError(
                f"A return can hold at most {MAX_RETURN_ITEMS} items."
            )
        return value

    def validate(self, attrs):
        wanted = [row["product_public_id"] for row in attrs["items"]]
        products = {
            product.public_id: product for product in Product.objects.filter(public_id__in=wanted)
        }
        missing = [public_id for public_id in wanted if public_id not in products]
        if missing:
            raise serializers.ValidationError(
                {"items": f"Unknown product(s): {', '.join(missing)}."}
            )
        attrs["resolved_items"] = items_from_payload(
            {**row, "product": products[row["product_public_id"]]} for row in attrs["items"]
        )
        return attrs


class AcceptReturnOrderSerializer(serializers.Serializer):
    """Request body to accept a return.

    ``include_in_other_raw_materials`` is required: it is the admin's explicit
    choice to book the packing materials back too. ``recipe_public_ids`` is the
    flat list of the recipes to book them against (live or soft-deleted); it
    must be empty or omitted when the flag is false.
    """

    include_in_other_raw_materials = serializers.BooleanField(
        error_messages={"required": "include_in_other_raw_materials is required."}
    )
    recipe_public_ids = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
        allow_empty=True,
        help_text=(
            "OMR-… recipes to book packing material against, one per material "
            "type per line. Required (covering every line) when the flag is true."
        ),
    )


# -- Output -------------------------------------------------------------------


class ReturnProductRefSerializer(serializers.Serializer):
    """Output shape for a ``{public_id, name}`` product reference."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class ReturnUserRefSerializer(serializers.Serializer):
    """Output shape for the user who raised, accepted or rejected a return."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class ReturnOrderRefSerializer(serializers.Serializer):
    """Output shape for the order a return is against."""

    public_id = serializers.CharField()
    status = serializers.CharField()


class ReturnClientRefSerializer(serializers.Serializer):
    """Output shape for the client on a return."""

    public_id = serializers.CharField()
    company_name = serializers.CharField()


class ReturnOrderItemPayloadSerializer(serializers.Serializer):
    """Output shape for one returned line."""

    product = ReturnProductRefSerializer()
    packet_weight = serializers.CharField()
    packets = serializers.IntegerField()
    kg = serializers.CharField(help_text="packets x packet_weight.")
    price_per_packet = serializers.CharField()
    line_total = serializers.CharField(help_text="packets x price_per_packet.")


class ReturnOrderListItemSerializer(serializers.Serializer):
    """Output shape for one return in a list (``return_order_list_payload``)."""

    public_id = serializers.CharField()
    status = serializers.CharField(help_text="RETURN_PENDING, RETURN_ACCEPTED or RETURN_REJECTED.")
    return_date = serializers.DateField()
    created_at = serializers.DateTimeField()
    order = ReturnOrderRefSerializer()
    client = ReturnClientRefSerializer()
    created_by = ReturnUserRefSerializer(allow_null=True, help_text="Sales person who raised it.")
    verified_by = ReturnUserRefSerializer(
        allow_null=True, help_text="Sales admin who accepted it; null unless ACCEPTED."
    )
    rejected_by = ReturnUserRefSerializer(
        allow_null=True, help_text="Sales admin who rejected it; null unless REJECTED."
    )
    items = ReturnOrderItemPayloadSerializer(many=True)
    total_kg = serializers.CharField()
    total_amount = serializers.CharField()


class ReturnOrderPayloadSerializer(ReturnOrderListItemSerializer):
    """Output shape for one return in full (``return_order_payload``)."""

    include_in_other_raw_materials = serializers.BooleanField(
        allow_null=True, help_text="Set on accept: whether packing material was booked too."
    )
    verified_at = serializers.DateTimeField(allow_null=True)
    rejected_at = serializers.DateTimeField(allow_null=True)
    inward_raw_materials = serializers.ListField(
        child=serializers.CharField(),
        help_text="IR-… lots the accept booked; empty unless ACCEPTED.",
    )
    inward_other_materials = serializers.ListField(
        child=serializers.CharField(),
        help_text="IO-… lots the accept booked; empty unless ACCEPTED.",
    )


class ReturnPrefillOrderSerializer(serializers.Serializer):
    """Output shape for the order summary on the prefill."""

    public_id = serializers.CharField()
    status = serializers.CharField()
    client = ReturnClientRefSerializer()


class ReturnPrefillLineSerializer(serializers.Serializer):
    """Output shape for one challan line on the prefill."""

    product = ReturnProductRefSerializer()
    packet_weight = serializers.CharField()
    dispatched_packets = serializers.IntegerField(help_text="Packets on the challan.")
    returnable_packets = serializers.IntegerField(
        help_text="Dispatched, less what a live return already claims."
    )
    suggested_price_per_packet = serializers.CharField(
        help_text="The order line's bag price divided by the packets in the bag."
    )


class ReturnOrderPrefillSerializer(serializers.Serializer):
    """Output shape for ``GET return-order/<order_public_id>``."""

    order = ReturnPrefillOrderSerializer()
    return_order = ReturnOrderPayloadSerializer(
        allow_null=True, help_text="The order's live return, if there is one."
    )
    lines = ReturnPrefillLineSerializer(many=True)


class ReturnRecipeOptionMaterialTypeSerializer(serializers.Serializer):
    """Output shape for a recipe's material type."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_type = serializers.CharField()


class ReturnRecipeOptionSerializer(serializers.Serializer):
    """Output shape for one recipe the admin may book a line's packing against."""

    public_id = serializers.CharField()
    material_type = ReturnRecipeOptionMaterialTypeSerializer()
    quantity = serializers.CharField(help_text="Material per packet, in the type's unit.")
    is_deleted = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    deleted_at = serializers.DateTimeField(allow_null=True)


class ReturnRecipeLineSerializer(serializers.Serializer):
    """Output shape for one return line with its candidate recipes."""

    product = ReturnProductRefSerializer()
    packet_weight = serializers.CharField()
    packets = serializers.IntegerField()
    recipes = ReturnRecipeOptionSerializer(many=True)


class ReturnOrderRecipesSerializer(serializers.Serializer):
    """Output shape for ``GET return-order-recipes/<public_id>``."""

    lines = ReturnRecipeLineSerializer(many=True)
