"""Waste-order creation endpoint: ``POST /api/sales-admin/create-waste-order``.

A sales admin books a **waste order**: a custom order made only from the waste
pool (``RawMaterialWaste``). It follows ``create-custom-order``, with two
differences:

* lines are **kilograms** of a product, not packets -- ``quantity_kg`` at a
  ``negotiated_selling_price`` **per kg**, which is required (waste is not sold
  at the product's normal rate);
* the stock gate is the product's **unused waste** (see
  ``InventoryOperations.waste_available_kg``), not the loose-packet pools, and
  raw stock is untouched.

The order is stored as a ``CustomOrder`` with ``made_from_waste`` true and
``unit_of_measure`` ``kg``. It is born ``CONFIRMED`` and can only be dispatched
afterwards. A shortfall in any product's waste is a 400 and nothing is written.

``WasteOrderItemWriteSerializer`` and ``resolve_waste_order_items`` are exported
and reused by ``edit-waste-order``.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ClientChildOrgOperations import resolve_child_org
from aggregator.CustomOrderOperations import (
    create_waste_order,
    custom_order_detail_payload,
)
from aggregator.models import CustomOrder, Product
from api.admin import AdminApiView
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CreateCustomOrderView import MAX_CUSTOM_ORDER_ITEMS, CreateCustomOrderSerializer
from .CustomOrderView import custom_order_detail_queryset


class WasteOrderItemWriteSerializer(serializers.Serializer):
    """One line of a waste order: kilograms of one product's waste."""

    product_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "product_public_id is required.",
            "required": "product_public_id is required.",
        },
    )
    quantity_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal("0.001"),
        help_text="Kilograms of this product's waste to sell.",
        error_messages={"required": "quantity_kg is required."},
    )
    negotiated_selling_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        help_text=(
            "Price per kg for this line. Required when booking an order or "
            "adding a line; on an edit, omit it to leave an existing line's "
            "price alone."
        ),
    )


def validate_waste_order_item_list(value: list[dict]) -> list[dict]:
    """The list-level rules shared by create and edit."""
    if not value:
        raise serializers.ValidationError("A waste order needs at least one item.")
    if len(value) > MAX_CUSTOM_ORDER_ITEMS:
        raise serializers.ValidationError(
            f"A waste order can hold at most {MAX_CUSTOM_ORDER_ITEMS} items."
        )
    ids = [item["product_public_id"] for item in value]
    if len(set(ids)) != len(ids):
        raise serializers.ValidationError(
            "The same product is listed twice -- combine it into one line with the total kg."
        )
    return value


def resolve_waste_order_items(
    items: list[dict], order: CustomOrder | None = None
) -> list[dict]:
    """Turn the submitted lines into the shape the operations take.

    One query for every product named, so unknown public ids are reported as a
    list. A deleted product cannot be *added*; on an edit (``order`` given) a
    product already on the order stays acceptable, because ``items`` is a full
    replacement and refusing it would make the order impossible to edit.
    """
    public_ids = [item["product_public_id"] for item in items]
    on_order: set[int] = set()
    if order is not None:
        on_order = set(order.items.values_list("product_id", flat=True))
    products = {
        product.public_id: product
        for product in Product.all_objects.filter(
            Q(is_deleted=False) | Q(id__in=on_order), public_id__in=public_ids
        )
    }
    missing = [
        public_id
        for public_id in public_ids
        if public_id not in products
        or (products[public_id].is_deleted and products[public_id].id not in on_order)
    ]
    if missing:
        raise serializers.ValidationError(
            {"items": f"Unknown product(s): {', '.join(missing)}."}
        )
    return [
        {
            "product": products[item["product_public_id"]],
            "quantity_kg": item["quantity_kg"],
            "negotiated_selling_price": item.get("negotiated_selling_price"),
        }
        for item in items
    ]


class CreateWasteOrderSerializer(CreateCustomOrderSerializer):
    """Request validation for booking a waste order (kg lines, price per kg required)."""

    items = WasteOrderItemWriteSerializer(many=True)
    hsn_code = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional free-text HSN code kept on the order.",
    )

    def validate_items(self, value: list[dict]) -> list[dict]:
        value = validate_waste_order_item_list(value)
        unpriced = [
            item["product_public_id"]
            for item in value
            if item.get("negotiated_selling_price") is None
        ]
        if unpriced:
            raise serializers.ValidationError(
                f"negotiated_selling_price (per kg) is required for: {', '.join(unpriced)}."
            )
        return value

    def resolve_items(self, items: list[dict]) -> list[dict]:
        return resolve_waste_order_items(items)


class CreateWasteOrderView(AdminApiView):
    """Book a waste order for any verified client (app admin only)."""

    serializer_class = CreateWasteOrderSerializer
    admin_required = True

    @extend_schema(
        summary="Book a waste order (kg, drawn from the waste pool)",
        request=CreateWasteOrderSerializer,
        responses={201: CustomOrderDetailPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateWasteOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            booked_for = (
                resolve_child_org(data["client"], data["booked_for"], request.user)
                if data.get("booked_for")
                else None
            )
            order = create_waste_order(
                client=data["client"],
                delivery_address=data["delivery_address"],
                actor=request.user,
                items=data["resolved_items"],
                special_comments=data["special_comments"],
                expected_delivery_date=data["expected_delivery_date"],
                booked_for=booked_for,
                hsn_code=data["hsn_code"],
            )
        order = custom_order_detail_queryset().get(pk=order.pk)
        return Response(custom_order_detail_payload(order), status=status.HTTP_201_CREATED)
