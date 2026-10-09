"""Custom-order creation endpoint: ``POST /api/sales-admin/create-custom-order``.

A sales admin books a **loose-packet** order: each line names a product, the
weight of one packet and how many packets, optionally at a negotiated
per-packet price (omitted, it is ``product.price_for_weight(packet_weight)``).
The whole order is created atomically: one bad line and nothing is written.

Only a sales admin can reach this -- a sales person cannot book a custom order,
and ``CustomOrder.clean()`` rejects a non-admin creator anyway.

Any **verified** client may be booked against, whoever onboarded it: a sales
admin works across every sales person's book.

A custom order has no separate verification step: it is born ``CONFIRMED``,
verified by the booking admin, and reserves its packets at once. So stock **is**
checked here -- every ``(product, packet_weight)`` pool must have the packets
(see ``CustomOrderOperations.assert_loose_stock_covers``); a shortfall is a 400.

``client_address_id`` is a **link** id, as on ``edit-order``: it resolves with
one lookup scoped to the client, so an address belonging to somebody else
simply does not match.

``CustomOrderItemWriteSerializer`` and ``resolve_custom_order_items`` are
exported and reused by ``edit-custom-order``.
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
    create_custom_order,
    custom_order_detail_payload,
)
from aggregator.models import Client, ClientAddress, CustomOrder, Product
from aggregator.models.Status import StatusIds
from api.admin import AdminApiView
from api.client_serializers import BookedForSerializer
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CustomOrderView import custom_order_detail_queryset

# Upper bound on distinct lines in one custom order -- a booking screen, not a
# bulk import. The same bound the bag order uses.
MAX_CUSTOM_ORDER_ITEMS = 100


class CustomOrderItemWriteSerializer(serializers.Serializer):
    """One line of a custom order: loose packets of one product at one weight."""

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
        help_text=(
            "Weight of one packet, in kg. Selects the loose pool the line draws "
            "from: 1kg and 0.5kg packets are separate stock."
        ),
        error_messages={"required": "packet_weight is required."},
    )
    packets = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "packets is required.",
            "min_value": "Packets must be at least 1.",
        },
    )
    negotiated_selling_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        help_text=(
            "Per-packet rate for this line. Omit it to leave an existing line's "
            "price alone, or to charge a new line the product's rate for this "
            "packet weight."
        ),
    )


def validate_custom_order_item_list(value: list[dict]) -> list[dict]:
    """The list-level rules shared by create and edit."""
    if not value:
        raise serializers.ValidationError("A custom order needs at least one item.")
    if len(value) > MAX_CUSTOM_ORDER_ITEMS:
        raise serializers.ValidationError(
            f"A custom order can hold at most {MAX_CUSTOM_ORDER_ITEMS} items."
        )
    keys = [(item["product_public_id"], item["packet_weight"]) for item in value]
    if len(set(keys)) != len(keys):
        raise serializers.ValidationError(
            "The same product and packet weight is listed twice -- "
            "combine them into one line with the total packets."
        )
    return value


def resolve_custom_order_items(
    items: list[dict], order: CustomOrder | None = None
) -> list[dict]:
    """Turn the submitted lines into the shape the operations take.

    One query for every product named, so an unknown public id is reported as
    a list rather than one id at a time.

    A deleted product cannot be *added*; it answers exactly like one that does
    not exist. On an edit (``order`` given) a ``(product, packet_weight)`` line
    already on the order stays acceptable, because ``items`` is a full
    replacement: refusing it would make an order booked before the deletion
    impossible to edit without dropping that line.
    """
    public_ids = [item["product_public_id"] for item in items]
    on_order: set[tuple[int, Decimal]] = set()
    if order is not None:
        on_order = set(order.items.values_list("product_id", "packet_weight"))
    products = {
        product.public_id: product
        for product in Product.all_objects.filter(
            Q(is_deleted=False) | Q(id__in=[product_id for product_id, _ in on_order]),
            public_id__in=public_ids,
        )
    }

    def usable(item: dict) -> bool:
        product = products.get(item["product_public_id"])
        if product is None:
            return False
        return not product.is_deleted or (product.id, item["packet_weight"]) in on_order

    missing = [item["product_public_id"] for item in items if not usable(item)]
    if missing:
        raise serializers.ValidationError(
            {"items": f"Unknown product(s): {', '.join(missing)}."}
        )
    return [
        {
            "product": products[item["product_public_id"]],
            "packet_weight": item["packet_weight"],
            "packets": item["packets"],
            "negotiated_selling_price": item.get("negotiated_selling_price"),
        }
        for item in items
    ]


class CreateCustomOrderSerializer(serializers.Serializer):
    """Request validation for booking a custom order."""

    client_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "client_public_id is required.",
            "required": "client_public_id is required.",
        },
    )
    client_address_id = serializers.IntegerField(
        error_messages={"required": "client_address_id is required."},
        help_text="A ClientAddress link id belonging to the client.",
    )
    special_comments = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    expected_delivery_date = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Defaults to the day after booking.",
    )
    items = CustomOrderItemWriteSerializer(many=True)
    booked_for = BookedForSerializer(
        required=False,
        allow_null=True,
        help_text=(
            "Optional child org the order is booked for: {id} to reuse one, or "
            "{party_name, village_name, ...} to get-or-create it."
        ),
    )

    def validate_items(self, value: list[dict]) -> list[dict]:
        return validate_custom_order_item_list(value)

    def resolve_items(self, items: list[dict]) -> list[dict]:
        """Turn the submitted lines into the operations' shape (overridden for waste orders)."""
        return resolve_custom_order_items(items)

    def validate(self, attrs: dict) -> dict:
        client = (
            Client.objects.filter(public_id=attrs["client_public_id"])
            .select_related("status")
            .first()
        )
        if client is None:
            raise serializers.ValidationError(
                {"client_public_id": f"Unknown client '{attrs['client_public_id']}'."}
            )
        # The same gate the bag order applies: an order records who it was
        # booked against, so the client must be fully verified.
        if (
            client.status_id != StatusIds.VERIFIED
            or client.verified_by_id is None
            or client.verified_at is None
        ):
            raise serializers.ValidationError(
                {
                    "client_public_id": (
                        f"Client '{attrs['client_public_id']}' is not verified."
                    )
                }
            )

        address_link = (
            ClientAddress.objects.filter(client=client, id=attrs["client_address_id"])
            .select_related("address")
            .first()
        )
        if address_link is None:
            raise serializers.ValidationError(
                {"client_address_id": "No such address for this client."}
            )

        attrs["client"] = client
        attrs["delivery_address"] = address_link.address
        attrs["resolved_items"] = self.resolve_items(attrs["items"])
        return attrs


class CreateCustomOrderView(AdminApiView):
    """Book a loose-packet custom order for any verified client (app admin only)."""

    serializer_class = CreateCustomOrderSerializer
    admin_required = True

    @extend_schema(
        summary="Book a custom (loose-packet) order",
        request=CreateCustomOrderSerializer,
        responses={201: CustomOrderDetailPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateCustomOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            booked_for = (
                resolve_child_org(data["client"], data["booked_for"], request.user)
                if data.get("booked_for")
                else None
            )
            order = create_custom_order(
                client=data["client"],
                delivery_address=data["delivery_address"],
                actor=request.user,
                items=data["resolved_items"],
                special_comments=data["special_comments"],
                expected_delivery_date=data["expected_delivery_date"],
                booked_for=booked_for,
            )
        order = custom_order_detail_queryset().get(pk=order.pk)
        return Response(custom_order_detail_payload(order), status=status.HTTP_201_CREATED)
