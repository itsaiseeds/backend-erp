"""Schema-only output serializers for the date-range exports (``/api/sales-admin/export/``).

Each class documents one row of an export's ``results`` exactly as the payload
builders produce it, nested down to plain fields, so the OpenAPI doc shows real
keys instead of ``additionalProp``. They reuse the list endpoints' serializers
wherever an export row embeds the same payload.
"""

from __future__ import annotations

from rest_framework import serializers

from api.order_serializers import (
    OrderItemPayloadSerializer,
    ProductRefSerializer,
    TransportAgencyRefSerializer,
)
from api.sales_admin.GetDispatchChallansView import DispatchChallanItemSerializer
from api.sales_admin.InwardOtherMaterialsView import InwardOtherMaterialPayloadSerializer
from api.sales_admin.InwardRawMaterialsView import InwardRawMaterialPayloadSerializer
from api.sales_admin.UpdateBagStockView import PackagingRefSerializer

# -- shared pieces ---------------------------------------------------------


class ExportClientSerializer(serializers.Serializer):
    """``ClientOperations.client_summary_payload``."""

    public_id = serializers.CharField()
    company_name = serializers.CharField()
    gst_number = serializers.CharField()


class ExportCitySerializer(serializers.Serializer):
    """``ClientOperations.order_city_payload``: the order's delivery city."""

    id = serializers.IntegerField()
    name = serializers.CharField()


# -- orders ------------------------------------------------------------------


class ExportOrderSerializer(serializers.Serializer):
    """One row of ``export/orders`` (``OrderOperations.order_export_payload``)."""

    public_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    client = ExportClientSerializer()
    city = ExportCitySerializer(
        allow_null=True, help_text="order -> delivery address -> city."
    )
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


class ExportCustomOrderItemSerializer(serializers.Serializer):
    """One loose-packet line of a custom order."""

    product = ProductRefSerializer()
    packet_weight = serializers.CharField(help_text="Weight of one packet, in kg.")
    negotiated_selling_price = serializers.CharField(help_text="Per packet.")
    packets = serializers.IntegerField()
    line_total = serializers.CharField()


class ExportCustomOrderSerializer(serializers.Serializer):
    """One row of ``export/custom-orders`` (``custom_order_export_payload``)."""

    public_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    client = ExportClientSerializer()
    city = ExportCitySerializer(
        allow_null=True, help_text="order -> delivery address -> city."
    )
    delivery_address = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    expected_delivery_date = serializers.DateField()
    actual_delivery_date = serializers.DateField(allow_null=True)
    special_comments = serializers.CharField(allow_blank=True)
    verified_at = serializers.DateTimeField(allow_null=True)
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField()
    items = ExportCustomOrderItemSerializer(many=True)


# -- dispatch receipts -------------------------------------------------------


class ExportDispatchReceiptSerializer(DispatchChallanItemSerializer):
    """One row of ``export/dispatch-receipts``: a full challan plus the order's own facts."""

    order_created_at = serializers.DateTimeField()
    city = ExportCitySerializer(
        allow_null=True, help_text="order -> delivery address -> city."
    )


# -- inward entries ----------------------------------------------------------


class ExportInwardRawMaterialSerializer(InwardRawMaterialPayloadSerializer):
    created_at = serializers.DateTimeField()


class ExportInwardOtherMaterialSerializer(InwardOtherMaterialPayloadSerializer):
    created_at = serializers.DateTimeField()


class ExportInwardDaySerializer(serializers.Serializer):
    """One row of ``export/inward-entries``: every entry booked on one IST day."""

    date = serializers.DateField()
    raw_materials = ExportInwardRawMaterialSerializer(many=True)
    other_materials = ExportInwardOtherMaterialSerializer(many=True)


# -- inventory snapshots -----------------------------------------------------


class ExportBagSnapshotSerializer(serializers.Serializer):
    """``InventoryOperations.snapshot_count_payload``: counted figures only."""

    public_id = serializers.CharField()
    snapshot_date = serializers.DateField()
    packaging = PackagingRefSerializer()
    bags = serializers.IntegerField()
    total_packets = serializers.IntegerField()
    total_weight = serializers.CharField(help_text="Kilograms.")


class ExportLooseSnapshotSerializer(serializers.Serializer):
    """``InventoryOperations.loose_stock_count_payload``: counted figures only."""

    public_id = serializers.CharField()
    snapshot_date = serializers.DateField()
    product = ProductRefSerializer()
    packet_weight = serializers.CharField(help_text="Weight of one packet, in kg.")
    packets = serializers.IntegerField()
    total_weight = serializers.CharField(help_text="Kilograms.")


class ExportSnapshotDaySerializer(serializers.Serializer):
    """One row of ``export/inventory-snapshots``: both counts for one date."""

    snapshot_date = serializers.DateField()
    bag_snapshots = ExportBagSnapshotSerializer(many=True)
    loose_snapshots = ExportLooseSnapshotSerializer(many=True)
