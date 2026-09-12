"""Order creation endpoint:
``POST /android/api/v1/create-multi-select-bag-order``.

A sales person books an order by multi-selecting bags from
``GET /android/api/v1/sales-person-catalogue`` and giving each a quantity. The
whole order is created atomically: one bad line and nothing is written.

This is a **bag** order -- sealed ``ProductPackaging`` units. Loose-packet
``CustomOrder``s are a sales-admin concern and are deliberately unreachable from
the app; ``CustomOrder.clean()`` rejects a non-admin creator anyway.

Only a **verified** client may be booked against: a client is born
``VERIFICATION_PENDING`` and stays unbookable until a sales admin approves it
through ``/api/sales-admin/verify-client/``.

No price may be sent. Each line is charged at the bag's own
``selling_price``, which ``OrderOperations.add_order_item`` fills in -- a sales
person does not negotiate from the app.

The order is born ``BOOKED``. Stock is **not** checked here: availability is the
sales admin's gate at verification time (``OrderOperations.verify_order``), so a
sales person can always book and let the office confirm.

``client_transport_agency_id`` is optional; omitting it books a private
(own-vehicle) dispatch, which is the default assumption.

Both ``client_address_id`` and ``client_transport_agency_id`` are **link** ids,
handed out verbatim by ``GET /android/api/v1/utilities/client-addresses`` and
``.../utilities/client-transport-agencies``. Naming the link rather than the
underlying row is what makes "does this belong to the client?" the lookup
itself rather than a second check.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import (
    Client,
    ClientAddress,
    ClientTransportAgency,
    ProductPackaging,
)
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import create_order, order_payload
from android.api.base import AndroidBaseView

# Upper bound on distinct bags in one order -- a booking screen, not a bulk import.
MAX_ORDER_ITEMS = 100


class BagOrderItemSerializer(serializers.Serializer):
    """One line of the order: a bag and how many of it."""

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


class TransportAgencyRefSerializer(serializers.Serializer):
    """Output shape for the ``transport_agency`` reference on an order."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class OrderItemPayloadSerializer(serializers.Serializer):
    """Output shape for one order line (schema only)."""

    packaging = serializers.DictField()
    negotiated_selling_price = serializers.CharField()
    quantity = serializers.IntegerField()
    line_total = serializers.CharField()


class OrderPayloadSerializer(serializers.Serializer):
    """Output shape for a booked order (schema only; built by hand)."""

    public_id = serializers.CharField()
    client = serializers.DictField()
    delivery_address = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    expected_delivery_date = serializers.DateField()
    actual_delivery_date = serializers.DateField(allow_null=True)
    special_comments = serializers.CharField(allow_blank=True)
    transport_agency = TransportAgencyRefSerializer(allow_null=True)
    dispatch_mode = serializers.ChoiceField(choices=["AGENCY", "PRIVATE"])
    verified_at = serializers.DateTimeField(allow_null=True)
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField()
    items = OrderItemPayloadSerializer(many=True)


class CreateMultiSelectBagOrderSerializer(serializers.Serializer):
    """Request validation for booking a bag order.

    The address and the agency arrive as *link* ids, so each resolves with a
    single lookup scoped to the client -- an id belonging to somebody else
    simply does not match, and the "belongs to this client" rule
    ``Order.clean()`` enforces is satisfied by construction.
    """

    client_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "client_public_id is required.",
            "required": "client_public_id is required.",
        },
    )
    client_address_id = serializers.IntegerField(
        error_messages={"required": "client_address_id is required."},
        help_text="A link id from GET /android/api/v1/utilities/client-addresses.",
    )
    client_transport_agency_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text=(
            "A link id from GET /android/api/v1/utilities/client-transport-agencies. "
            "Omit or send null for a private (own-vehicle) dispatch."
        ),
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
    items = BagOrderItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        if len(value) > MAX_ORDER_ITEMS:
            raise serializers.ValidationError(
                f"An order may not have more than {MAX_ORDER_ITEMS} items."
            )
        public_ids = [item["product_packaging_public_id"] for item in value]
        if len(set(public_ids)) != len(public_ids):
            raise serializers.ValidationError(
                "The same product packaging is listed twice -- "
                "combine them into one line with the total quantity."
            )
        return value

    def validate(self, attrs):
        # Scoped to ``created_by`` like every other client endpoint: another
        # sales person's client reads as unknown rather than as forbidden.
        client = Client.objects.filter(
            public_id=attrs["client_public_id"],
            created_by=self.context["request"].user,
        ).first()
        if client is None:
            raise serializers.ValidationError(
                {"client_public_id": f"Unknown client '{attrs['client_public_id']}'."}
            )
        # A client is born VERIFICATION_PENDING and only a sales admin can
        # promote it. ``verified_by`` / ``verified_at`` are checked alongside
        # the status because an order records who it was booked against, and a
        # half-verified client would leave that unanswerable. (Client.clean()
        # keeps the three in step, so this is belt-and-braces.)
        if (
            client.status.id != StatusIds.VERIFIED
            or client.verified_by is None
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
                {
                    "client_address_id": (
                        "Delivery address must be one of this client's addresses."
                    )
                }
            )

        agency = None
        if attrs.get("client_transport_agency_id") is not None:
            agency_link = (
                ClientTransportAgency.objects.filter(
                    client=client, id=attrs["client_transport_agency_id"]
                )
                .select_related("transport_agency")
                .first()
            )
            if agency_link is None:
                raise serializers.ValidationError(
                    {
                        "client_transport_agency_id": (
                            "Transport agency must be one of this client's agencies."
                        )
                    }
                )
            agency = agency_link.transport_agency

        # One query for every line, so a 100-item order does not become 100.
        wanted = [item["product_packaging_public_id"] for item in attrs["items"]]
        packagings = {
            packaging.public_id: packaging
            for packaging in ProductPackaging.objects.filter(public_id__in=wanted)
        }
        missing = [public_id for public_id in wanted if public_id not in packagings]
        if missing:
            raise serializers.ValidationError(
                {"items": f"Unknown product packaging(s): {', '.join(missing)}."}
            )

        attrs["client"] = client
        attrs["delivery_address"] = address_link.address
        attrs["transport_agency"] = agency
        attrs["resolved_items"] = [
            {
                "product_packaging": packagings[item["product_packaging_public_id"]],
                "quantity": item["quantity"],
            }
            for item in attrs["items"]
        ]
        return attrs


class CreateMultiSelectBagOrderView(AndroidBaseView):
    """Book an order of sealed bags for one of the caller's clients."""

    serializer_class = CreateMultiSelectBagOrderSerializer

    @extend_schema(
        operation_id="android_api_v1_create_multi_select_bag_order",
        summary="Book an order from multi-selected catalogue bags",
        request=CreateMultiSelectBagOrderSerializer,
        responses={201: OrderPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateMultiSelectBagOrderSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = create_order(
            client=data["client"],
            delivery_address=data["delivery_address"],
            actor=request.user,
            items=data["resolved_items"],
            special_comments=data["special_comments"],
            expected_delivery_date=data["expected_delivery_date"],
            transport_agency=data["transport_agency"],
        )
        return Response(order_payload(order), status=status.HTTP_201_CREATED)
