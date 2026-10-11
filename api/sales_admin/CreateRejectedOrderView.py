"""Rejected-order creation endpoint: ``POST /api/sales-admin/create-rejected-order``.

A sales admin sells **specific lab-rejected lots** to a client. Each line names a
lot (``inward_raw_material_public_id``), the kilograms to sell and a
``negotiated_selling_price`` **per kg**, which is required. A lot must be
rejected, dated and live, and the kg cannot exceed what earlier rejected orders
left of it (see ``InventoryOperations.rejected_lot_remaining_kg``).

Booking **is** the dispatch: the order goes out on our own vehicle straight away,
so the driver and vehicle are required, the date is today and the destination the
delivery address's city. The order is stored as a ``CustomOrder`` with
``made_from_rejected`` set and ends DISPATCHED, its challan written; each line
takes an optional ``lot_number`` (default: the lot's own ``lot_no``). No stock-ledger figure moves.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ClientChildOrgOperations import resolve_child_org
from aggregator.CustomOrderOperations import (
    create_rejected_order,
    custom_order_detail_payload,
)
from aggregator.models import City, InwardRawMaterial
from aggregator.OrderOperations import OWN_VEHICLE_FIELD_REQUIRED
from api.admin import AdminApiView
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CreateCustomOrderView import MAX_CUSTOM_ORDER_ITEMS, CreateCustomOrderSerializer
from .CustomOrderView import custom_order_detail_queryset


def _own_vehicle_field(field: str, **kwargs) -> serializers.CharField:
    message = OWN_VEHICLE_FIELD_REQUIRED.format(field=field)
    return serializers.CharField(error_messages={"required": message, "blank": message}, **kwargs)


class RejectedOrderItemWriteSerializer(serializers.Serializer):
    """One line of a rejected order: kilograms of one rejected lot."""

    inward_raw_material_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "inward_raw_material_public_id is required.",
            "required": "inward_raw_material_public_id is required.",
        },
    )
    quantity_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal("0.001"),
        help_text="Kilograms of this lot to sell.",
        error_messages={"required": "quantity_kg is required."},
    )
    negotiated_selling_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        help_text="Price per kg for this line.",
        error_messages={"required": "negotiated_selling_price (per kg) is required."},
    )
    lot_number = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        default="",
        help_text=(
            "The lot number printed on this line of the challan. Omit it to print "
            "the lot's own lot_no."
        ),
    )


class CreateRejectedOrderSerializer(CreateCustomOrderSerializer):
    """Request validation for booking a rejected order (lot lines, price per kg required)."""

    items = RejectedOrderItemWriteSerializer(many=True)
    hsn_code = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional free-text HSN code kept on the order.",
    )
    from_city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        error_messages={"required": "from_city_id is required."},
        help_text="Where the goods left from.",
    )
    driver_name = _own_vehicle_field("driver_name", max_length=255)
    driver_number = _own_vehicle_field("driver_number", max_length=10)
    vehicle_number = _own_vehicle_field("vehicle_number", max_length=32)

    def validate_driver_number(self, value: str) -> str:
        from authentication.validators import validate_phone_number

        validate_phone_number(value)
        return value

    def validate_items(self, value: list[dict]) -> list[dict]:
        if not value:
            raise serializers.ValidationError("A rejected order needs at least one item.")
        if len(value) > MAX_CUSTOM_ORDER_ITEMS:
            raise serializers.ValidationError(
                f"A rejected order can hold at most {MAX_CUSTOM_ORDER_ITEMS} items."
            )
        ids = [item["inward_raw_material_public_id"] for item in value]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError(
                "The same lot is listed twice -- combine it into one line with the total kg."
            )
        return value

    def resolve_items(self, items: list[dict]) -> list[dict]:
        public_ids = [item["inward_raw_material_public_id"] for item in items]
        lots = {
            lot.public_id: lot
            for lot in InwardRawMaterial.objects.filter(public_id__in=public_ids).select_related(
                "product"
            )
        }
        missing = [public_id for public_id in public_ids if public_id not in lots]
        if missing:
            raise serializers.ValidationError(
                {"items": f"Unknown lot(s): {', '.join(missing)}."}
            )
        return [
            {
                "lot": lots[item["inward_raw_material_public_id"]],
                "quantity_kg": item["quantity_kg"],
                "negotiated_selling_price": item["negotiated_selling_price"],
                "lot_number": item["lot_number"],
            }
            for item in items
        ]


class CreateRejectedOrderView(AdminApiView):
    """Sell rejected lots to a verified client, dispatched at once (app admin only)."""

    serializer_class = CreateRejectedOrderSerializer
    admin_required = True

    @extend_schema(
        summary="Book and dispatch a rejected order (kg of specific rejected lots)",
        request=CreateRejectedOrderSerializer,
        responses={201: CustomOrderDetailPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateRejectedOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            booked_for = (
                resolve_child_org(data["client"], data["booked_for"], request.user)
                if data.get("booked_for")
                else None
            )
            order = create_rejected_order(
                client=data["client"],
                delivery_address=data["delivery_address"],
                actor=request.user,
                items=data["resolved_items"],
                from_city=data["from_city_id"],
                driver_name=data["driver_name"],
                driver_number=data["driver_number"],
                vehicle_number=data["vehicle_number"],
                special_comments=data["special_comments"],
                expected_delivery_date=data["expected_delivery_date"],
                booked_for=booked_for,
                hsn_code=data["hsn_code"],
            )
        order = custom_order_detail_queryset().get(pk=order.pk)
        return Response(custom_order_detail_payload(order), status=status.HTTP_201_CREATED)
