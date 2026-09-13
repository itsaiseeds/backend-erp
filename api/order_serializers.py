"""Schema-only output serializers for the order endpoints.

Order payloads are built by hand in ``aggregator.OrderOperations``; these
classes exist so drf-spectacular can document the shape those functions return.
Shared between the Android app and the sales-admin website, exactly as
``api.client_serializers`` is -- the two sides render the same order.
"""

from __future__ import annotations

from rest_framework import serializers

from api.client_serializers import ClientPayloadSerializer


class TransportAgencyRefSerializer(serializers.Serializer):
    """Output shape for the ``transport_agency`` reference on an order."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class PackagingPayloadSerializer(serializers.Serializer):
    """Output shape for one bag (``ProductOperations.packaging_payload``)."""

    public_id = serializers.CharField()
    product = serializers.DictField(
        help_text="The bag's product: {public_id, name}.",
    )
    packet_weight = serializers.CharField()
    packets = serializers.IntegerField()
    total_weight = serializers.CharField()
    selling_price = serializers.CharField()


class OrderCardProductSerializer(serializers.Serializer):
    """Output shape for the product a bag on an order *card* holds.

    Wider than ``packaging_payload``'s own ``product`` block by exactly one
    field: the picture the card renders. ``packaging_payload`` is left alone
    because it is embedded in every order payload and across the sales-admin
    API, where the image does not belong.
    """

    public_id = serializers.CharField()
    name = serializers.CharField()
    image_url = serializers.CharField(
        allow_blank=True,
        help_text=(
            "The product's picture: an absolute URL when deployed, a "
            "MEDIA_URL-relative path in development, empty when none is set."
        ),
    )


class OrderCardPackagingSerializer(serializers.Serializer):
    """Output shape for one bag on an order card, and how many of it.

    One entry per order line. The bag is the unit an order is placed in, so two
    sizes of the same seed are two entries rather than one product listed twice.
    """

    public_id = serializers.CharField()
    product = OrderCardProductSerializer()
    packet_weight = serializers.CharField()
    packets = serializers.IntegerField()
    total_weight = serializers.CharField()
    selling_price = serializers.CharField(
        help_text="The bag's own list price, not what this order was charged."
    )
    quantity = serializers.IntegerField(help_text="Bags of this kind on the order.")


class OrderItemPayloadSerializer(serializers.Serializer):
    """Output shape for one order line (schema only)."""

    packaging = PackagingPayloadSerializer()
    negotiated_selling_price = serializers.CharField()
    quantity = serializers.IntegerField()
    line_total = serializers.CharField()


class OrderDetailPayloadSerializer(serializers.Serializer):
    """Output shape for one order in full (``order_detail_payload``).

    Identical to the Android booking response except that ``client`` carries the
    whole client -- every address and transport agency, each with its link id --
    rather than just the company name and GST number.
    """

    public_id = serializers.CharField()
    client = ClientPayloadSerializer()
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
