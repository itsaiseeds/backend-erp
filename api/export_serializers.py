"""Schema-only output serializers for the date-range exports (``/api/sales-admin/export/``).

Each class documents one row of an export's ``results`` exactly as the payload
builders produce it, nested down to plain fields, so the OpenAPI doc shows real
keys instead of ``additionalProp``. They reuse the list endpoints' serializers
wherever an export row embeds the same payload.
"""

from __future__ import annotations

from rest_framework import serializers

from api.client_serializers import ChildOrgPayloadSerializer
from api.field_trip_serializers import (
    FarmerVisitPayloadSerializer,
    IdNameSerializer,
    UserContactRefSerializer,
)
from api.inward_serializers import (
    InwardOtherMaterialPayloadSerializer,
    InwardRawMaterialPayloadSerializer,
)
from api.order_serializers import (
    OrderItemPayloadSerializer,
    ProductRefSerializer,
    TransportAgencyRefSerializer,
)
from api.sales_admin.GetDispatchChallansView import (
    CustomDispatchChallanItemSerializer,
    DispatchChallanItemSerializer,
)
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
    city = ExportCitySerializer(allow_null=True, help_text="order -> delivery address -> city.")
    delivery_address = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    expected_delivery_date = serializers.DateField()
    actual_delivery_date = serializers.DateField(allow_null=True)
    special_comments = serializers.CharField(allow_blank=True)
    transport_agency = TransportAgencyRefSerializer(allow_null=True)
    dispatch_mode = serializers.ChoiceField(choices=["AGENCY", "PRIVATE"])
    booked_for = ChildOrgPayloadSerializer(allow_null=True)
    verified_at = serializers.DateTimeField(allow_null=True)
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField()
    items = OrderItemPayloadSerializer(many=True)


class ExportCustomOrderItemSerializer(serializers.Serializer):
    """One loose-packet line of a custom order."""

    product = ProductRefSerializer()
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
    line_total = serializers.CharField()


class ExportCustomOrderSerializer(serializers.Serializer):
    """One row of ``export/custom-orders`` (``custom_order_export_payload``)."""

    public_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    client = ExportClientSerializer()
    city = ExportCitySerializer(allow_null=True, help_text="order -> delivery address -> city.")
    delivery_address = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    expected_delivery_date = serializers.DateField()
    actual_delivery_date = serializers.DateField(allow_null=True)
    special_comments = serializers.CharField(allow_blank=True)
    booked_for = ChildOrgPayloadSerializer(allow_null=True)
    verified_at = serializers.DateTimeField(allow_null=True)
    made_from_waste = serializers.BooleanField()
    unit_of_measure = serializers.ChoiceField(choices=["packet", "kg"])
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField()
    total_kg = serializers.CharField()
    items = ExportCustomOrderItemSerializer(many=True)


# -- dispatch receipts -------------------------------------------------------


class ExportDispatchReceiptSerializer(DispatchChallanItemSerializer):
    """One row of ``export/dispatch-receipts``: a full challan plus the order's own facts."""

    order_created_at = serializers.DateTimeField()
    city = ExportCitySerializer(allow_null=True, help_text="order -> delivery address -> city.")


class ExportCustomDispatchReceiptSerializer(CustomDispatchChallanItemSerializer):
    """A custom order's row of ``export/dispatch-receipts``."""

    order_created_at = serializers.DateTimeField()
    city = ExportCitySerializer(
        allow_null=True, help_text="custom order -> delivery address -> city."
    )


# -- inward entries ----------------------------------------------------------


class ExportInwardRawMaterialSerializer(InwardRawMaterialPayloadSerializer):
    created_by = None  # exports carry no audit keys; the lot payloads do
    created_at = serializers.DateTimeField()


class ExportInwardOtherMaterialSerializer(InwardOtherMaterialPayloadSerializer):
    created_by = None  # exports carry no audit keys; the lot payloads do
    created_at = serializers.DateTimeField()


class ExportInwardDaySerializer(serializers.Serializer):
    """One row of ``export/inward-entries``: every entry booked on one IST day."""

    date = serializers.DateField()
    raw_materials = ExportInwardRawMaterialSerializer(many=True)
    other_materials = ExportInwardOtherMaterialSerializer(many=True)


# -- inventory snapshots -----------------------------------------------------
#
# Unlike the other exports, ``export/inventory-snapshots`` is paginated: bag
# and loose rows are interleaved into one flat list ordered by snapshot_date,
# each carrying a ``kind`` discriminator instead of being grouped into a
# per-date bucket. See ``api.sales_admin.ExportInventorySnapshotsView``.


class ExportBagSnapshotSerializer(serializers.Serializer):
    """``InventoryOperations.snapshot_count_payload``: counted figures only,
    plus the ``kind`` discriminator."""

    kind = serializers.ChoiceField(choices=["bag"])
    public_id = serializers.CharField()
    snapshot_date = serializers.DateField()
    packaging = PackagingRefSerializer()
    bags = serializers.IntegerField()
    total_packets = serializers.IntegerField()
    total_weight = serializers.CharField(help_text="Kilograms.")


class ExportLooseSnapshotSerializer(serializers.Serializer):
    """``InventoryOperations.loose_stock_count_payload``: counted figures only,
    plus the ``kind`` discriminator."""

    kind = serializers.ChoiceField(choices=["loose"])
    public_id = serializers.CharField()
    snapshot_date = serializers.DateField()
    product = ProductRefSerializer()
    packet_weight = serializers.CharField(help_text="Weight of one packet, in kg.")
    packets = serializers.IntegerField()
    total_weight = serializers.CharField(help_text="Kilograms.")


# -- farmer visits -------------------------------------------------------------


class ExportFarmerVisitFieldTripSerializer(serializers.Serializer):
    """The trip a farmer was met on (``FieldTripOperations.farmer_visit_export_payload``)."""

    public_id = serializers.CharField()
    village = serializers.CharField()
    city = IdNameSerializer()


class ExportFarmerVisitSerializer(FarmerVisitPayloadSerializer):
    """``FieldTripOperations.farmer_visit_export_payload``: a visit, its trip and sales person."""

    field_trip = ExportFarmerVisitFieldTripSerializer(
        allow_null=True, help_text="Null for a farmer recorded outside any trip."
    )
    sales_person = UserContactRefSerializer()
