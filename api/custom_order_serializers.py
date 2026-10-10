"""Schema-only output serializers for the sales-admin custom-order endpoints.

Custom-order payloads are built by hand in ``aggregator.CustomOrderOperations``;
these classes exist so drf-spectacular can document the shape those functions
return -- the same arrangement ``api.order_serializers`` has for orders.
"""

from __future__ import annotations

from rest_framework import serializers

from api.client_serializers import (
    ChildOrgPayloadSerializer,
    ChildOrgSummarySerializer,
    ClientPayloadSerializer,
)
from api.order_serializers import OrderCardProductSerializer, ProductRefSerializer
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    SortCatalogueEntrySerializer,
)


class CustomOrderItemPayloadSerializer(serializers.Serializer):
    """Output shape for one line of a custom order: loose packets, or kg on a waste order."""

    product = ProductRefSerializer()
    packet_weight = serializers.CharField(
        allow_null=True, help_text="Weight of one packet, in kg. Null on a waste order's kg line."
    )
    negotiated_selling_price = serializers.CharField(
        help_text="Per packet, or per kg on a waste order's line."
    )
    packets = serializers.IntegerField(allow_null=True, help_text="Null on a kg line.")
    quantity_kg = serializers.CharField(
        allow_null=True, help_text="Kilograms on a waste order's line. Null on a packet line."
    )
    line_total = serializers.CharField()


class CustomOrderDetailPayloadSerializer(serializers.Serializer):
    """Output shape for one custom order in full (``custom_order_detail_payload``).

    ``client`` carries the whole client -- every address with its link id -- so
    the edit screen's address picker needs no second call.
    """

    public_id = serializers.CharField()
    client = ClientPayloadSerializer()
    delivery_address = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    expected_delivery_date = serializers.DateField()
    actual_delivery_date = serializers.DateField(allow_null=True)
    special_comments = serializers.CharField(allow_blank=True)
    booked_for = ChildOrgPayloadSerializer(allow_null=True)
    verified_at = serializers.DateTimeField(allow_null=True)
    made_from_waste = serializers.BooleanField()
    unit_of_measure = serializers.ChoiceField(choices=["packet", "kg"])
    hsn_code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Free-text HSN code. Present on waste orders only.",
    )
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField(help_text="0 on a waste order.")
    total_kg = serializers.CharField(help_text="0 on a packet order.")
    items = CustomOrderItemPayloadSerializer(many=True)


class CustomOrderListClientSerializer(serializers.Serializer):
    """Output shape for the ``client`` reference on a custom-order card."""

    public_id = serializers.CharField()
    company_name = serializers.CharField()


class CustomOrderListCitySerializer(serializers.Serializer):
    """Output shape for the ``city`` reference on a custom-order card."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class CustomOrderCardItemSerializer(serializers.Serializer):
    """Output shape for one line on a custom-order card."""

    product = OrderCardProductSerializer()
    packet_weight = serializers.CharField(
        allow_null=True, help_text="Weight of one packet, in kg. Null on a kg line."
    )
    negotiated_selling_price = serializers.CharField(
        help_text="Per packet, or per kg on a waste order's line."
    )
    packets = serializers.IntegerField(allow_null=True, help_text="Null on a kg line.")
    quantity_kg = serializers.CharField(
        allow_null=True, help_text="Kilograms on a waste order's line. Null on a packet line."
    )


class CustomOrderListItemSerializer(serializers.Serializer):
    """Output shape for one custom-order card (schema only)."""

    public_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    status = serializers.CharField(allow_null=True)
    client = CustomOrderListClientSerializer()
    client_created_by = serializers.CharField(
        allow_null=True, help_text="Sales person who onboarded the client."
    )
    created_by = serializers.CharField(
        allow_null=True, help_text="Sales admin who booked the custom order."
    )
    verified_by = serializers.CharField(
        allow_null=True,
        help_text="Sales admin who confirmed it -- the booking admin, by construction.",
    )
    delivery_address = serializers.CharField()
    city = CustomOrderListCitySerializer(allow_null=True)
    expected_delivery_date = serializers.DateField()
    booked_for = ChildOrgSummarySerializer(allow_null=True)
    made_from_waste = serializers.BooleanField()
    unit_of_measure = serializers.ChoiceField(choices=["packet", "kg"])
    hsn_code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Free-text HSN code. Present on waste orders only.",
    )
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField(help_text="0 on a waste order.")
    total_kg = serializers.CharField(help_text="0 on a packet order.")
    item_count = serializers.IntegerField()
    items = CustomOrderCardItemSerializer(many=True)


class CustomOrderListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = CustomOrderListItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)
