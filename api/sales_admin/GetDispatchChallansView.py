"""Challan list endpoint: ``GET /api/sales-admin/dispatch-challans/``.

Every dispatched order **and custom order**, each row carrying its challan in
full: our own consignor block, the consignee as it stood at dispatch time, the
HSN code, the financial year, the journey, and every line with its lot number.

The two kinds are one list, paged and sorted together, because both challans
live in ``DispatchEntry`` -- the list pages over entries rather than orders. An
order's row is exactly what it always was. A custom order's row has the same
envelope (``order_public_id`` is its ``CORD-…`` id) plus ``order_type:
"CUSTOM_ORDER"``, and its lines are loose packets: a product, a packet weight
and a packet count instead of a bag. A custom order always goes on our own
vehicle.

**A dispatch is listed as soon as it is recorded**, whichever way the goods went.
An agency dispatch is no longer held back until its ``lr_number`` arrives: the
transporter issues the consignment note *after* collection, so waiting for it hid
a dispatch that had physically happened -- the order was DISPATCHED, the goods
were on the road, and this list showed nothing. A blank LR is a pending detail,
not an incomplete challan, and ``upload-lr-number`` fills it in on a row that is
already here.

What a row does need is for the order to still **be** dispatched -- status
DISPATCHED or DELIVERED -- and to have a live ``dispatch_entry``, the challan
record written at dispatch. The two are not the same check: ``revert-dispatch`` rewinds the status
but deliberately leaves the dispatch rows attached, so without the status gate a
reverted order would keep printing a challan for goods that are back on the
shelf.

Unlike ``GET /orders/``, the **date window is required**: a challan list is read
for a period -- a week's dispatches, a month's -- never as "everything ever". It
filters on ``dispatch_entry__dispatched_at`` rather than the order's own
``created_at``: a challan belongs to the period the goods left in, not the period
the order was booked in. That column is on the entry rather than on either
dispatch row because a private dispatch has no ``DispatchDetails`` to read a
timestamp from, and it is a timestamp rather than ``dispatch_date`` because the
window bounds are datetimes.

Filterable by client and destination city, sortable by dispatch date (default,
newest first) or by when the order was booked.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet
from django.db.models.functions import Coalesce
from drf_spectacular.utils import (
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_field,
)
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.DispatchOperations import challan_entry_payload
from aggregator.models import DispatchEntry, DispatchEntryItem
from aggregator.models.Order import DISPATCH_REQUIRED_STATUS_CODES
from api.order_serializers import ProductRefSerializer, TransportAgencyRefSerializer
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_int,
    parse_str,
)

# What makes a challan listable, per kind of order. Declared once: the list view
# filters on it and the option providers below reuse it, so a picker can never
# offer a client or a city with nothing behind it.
#
# The status codes come from ``DISPATCH_REQUIRED_STATUS_CODES`` rather than being
# spelled out, so this list follows the enum if the lifecycle ever gains a
# post-dispatch status.
#
# The status **is** the whole rule. There is deliberately no clause on the LR
# number: an agency dispatch is listed with a blank one and ``upload-lr-number``
# fills it in later (see the module docstring). ``is_deleted`` is explicit on the
# order because a lookup spanning the relation does not pick up its soft-delete
# manager.


def _dispatched_challan_q(path: str) -> Q:
    """A live challan whose order at ``path`` is still dispatched.

    ``path`` is ``order`` or ``custom_order`` -- an entry names exactly one.
    """
    return Q(
        **{
            f"{path}__isnull": False,
            f"{path}__is_deleted": False,
            f"{path}__status__code__in": DISPATCH_REQUIRED_STATUS_CODES,
        }
    )


CHALLAN_Q = _dispatched_challan_q("order") | _dispatched_challan_q("custom_order")


def challan_entries() -> QuerySet:
    """Every live challan of a still-dispatched order, for either kind of order.

    ``order_created_at`` is when the order (or custom order) was booked -- the
    ``created_at`` sort and the dispatch-receipt export's window read it.
    """
    return DispatchEntry.objects.filter(CHALLAN_Q).annotate(
        order_created_at=Coalesce("order__created_at", "custom_order__created_at")
    )


def challan_queryset() -> QuerySet:
    """:func:`challan_entries` with every join the challan payloads walk.

    The payloads read the receiver off the ``DispatchEntry`` snapshot, so it is
    the entry's own address and cities that are selected here, not the order's
    or the client's. Shared by the challan list and the dispatch-receipt export.
    """
    return challan_entries().select_related(
        "order__transport_agency",
        "custom_order",
        "dispatch_details",
        "client",
        "client_address__pincode",
        "client_address__city",
        "client_address__state",
        "client_address__country",
        "from_city",
        "to_city",
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=DispatchEntryItem.objects.select_related(
                "product_packaging__product", "product"
            ),
        ),
    )


class ChallanPartySerializer(serializers.Serializer):
    """Output shape for our own consignor block (schema only)."""

    company_name = serializers.CharField()
    company_address = serializers.CharField()
    gst_number = serializers.CharField()
    state_name = serializers.CharField()


class ChallanAddressSerializer(serializers.Serializer):
    """Output shape for the consignee's address, as snapshotted at dispatch."""

    line_1 = serializers.CharField()
    line_2 = serializers.CharField()
    pincode = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()
    city_id = serializers.IntegerField()
    state_id = serializers.IntegerField()
    country_id = serializers.IntegerField()


class ChallanReceiverSerializer(serializers.Serializer):
    """Output shape for the consignee block (schema only)."""

    company_name = serializers.CharField()
    gst_number = serializers.CharField()
    address = ChallanAddressSerializer()
    contact_person_name = serializers.CharField()
    contact_person_number = serializers.CharField()


class ChallanDispatchSerializer(serializers.Serializer):
    """Output shape for the journey block (schema only)."""

    public_id = serializers.CharField()
    challan_number = serializers.CharField(
        help_text="The dated serial on the challan: YYYYMMDD-XXXX."
    )
    lr_number = serializers.CharField()
    dispatch_date = serializers.DateField()
    is_private = serializers.BooleanField()
    vehicle_number = serializers.CharField()
    driver_name = serializers.CharField()
    driver_number = serializers.CharField()
    from_city = serializers.CharField()
    to_city = serializers.CharField()
    transport_agency = TransportAgencyRefSerializer(
        allow_null=True, help_text="The carrier; null on a private dispatch."
    )


class ChallanLineSerializer(serializers.Serializer):
    """Output shape for one challan line: a bag, its lot and its money."""

    public_id = serializers.CharField(help_text="The packaging's public id.")
    product = ProductRefSerializer()
    packet_weight = serializers.CharField()
    packets = serializers.IntegerField()
    total_weight = serializers.CharField()
    selling_price = serializers.CharField()
    lot_number = serializers.CharField()
    quantity = serializers.IntegerField()
    negotiated_selling_price = serializers.CharField()
    line_total = serializers.CharField()


class DispatchChallanItemSerializer(serializers.Serializer):
    """Output shape for one challan (schema only)."""

    order_public_id = serializers.CharField()
    our_details = ChallanPartySerializer()
    receiver_details = ChallanReceiverSerializer()
    hsn_code = serializers.CharField()
    financial_year = serializers.CharField(help_text='Indian FY, e.g. "2026-2027".')
    dispatch = ChallanDispatchSerializer()
    items = ChallanLineSerializer(many=True)
    item_count = serializers.IntegerField()
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField()


class CustomChallanLineSerializer(serializers.Serializer):
    """Output shape for one custom-order challan line: loose packets, a lot, money."""

    product = ProductRefSerializer()
    packet_weight = serializers.CharField(help_text="Weight of one packet, in kg.")
    packets = serializers.IntegerField()
    lot_number = serializers.CharField()
    negotiated_selling_price = serializers.CharField(help_text="Per packet.")
    line_total = serializers.CharField()


class CustomDispatchChallanItemSerializer(serializers.Serializer):
    """Output shape for one custom order's challan (schema only)."""

    order_public_id = serializers.CharField(help_text="The custom order's CORD-… id.")
    order_type = serializers.ChoiceField(choices=["CUSTOM_ORDER"])
    our_details = ChallanPartySerializer()
    receiver_details = ChallanReceiverSerializer()
    hsn_code = serializers.CharField()
    financial_year = serializers.CharField(help_text='Indian FY, e.g. "2026-2027".')
    dispatch = ChallanDispatchSerializer()
    items = CustomChallanLineSerializer(many=True)
    item_count = serializers.IntegerField()
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField()


class DispatchChallanPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = serializers.SerializerMethodField()
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)

    @extend_schema_field(
        # ``resource_type_field_name=None``: an order row carries no type field
        # (its contract predates custom orders), so there is no discriminator.
        PolymorphicProxySerializer(
            component_name="DispatchChallanRow",
            serializers=[DispatchChallanItemSerializer, CustomDispatchChallanItemSerializer],
            resource_type_field_name=None,
            many=True,
        )
    )
    def get_results(self, obj: dict) -> list[dict]:
        return obj["results"]


def _clients_with_challans(request: Request) -> list[dict]:
    """Every distinct client that has a challan -- the client picker's options."""
    rows = (
        challan_entries()
        .values_list("client_id", "client__company_name")
        .distinct()
        .order_by("client__company_name")
    )
    return [{"value": client_id, "label": name} for client_id, name in rows]


def _challan_destination_cities(request: Request) -> list[dict]:
    """Every distinct city a challan was sent to."""
    rows = (
        challan_entries()
        .values_list("to_city_id", "to_city__name")
        .distinct()
        .order_by("to_city__name")
    )
    return [{"value": city_id, "label": name} for city_id, name in rows]


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "client",
        label="Client",
        lookup="client_id__in",
        parse=parse_int,
        description="Client id(s) the goods were consigned to (see options).",
        options=_clients_with_challans,
    ),
    QuerysetFilter(
        "city_id",
        label="Destination City",
        lookup="to_city_id__in",
        parse=parse_int,
        description="City id(s) the goods were sent to (see options).",
        options=_challan_destination_cities,
    ),
    # Free text rather than a picker: the point is to look up the number a
    # client read off their copy, and there is no useful option list for it.
    QuerysetFilter(
        "challan_number",
        label="Challan Number",
        lookup="challan_number__icontains",
        parse=parse_str,
        multi=False,
        description=(
            "Case-insensitive substring of the challan number (YYYYMMDD-XXXX). "
            "The date window still applies -- the number carries its own date."
        ),
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "dispatch_date",
        label="Dispatch Date",
        fields=("dispatched_at",),
        description="When the goods left (default: newest first).",
    ),
    SortOption(
        "created_at",
        label="Order Created",
        fields=("order_created_at",),
        description="When the order (or custom order) was booked.",
    ),
)


class GetDispatchChallansView(AdminPaginatedDateRangeListView):
    """List the delivery challans of dispatched orders and custom orders."""

    date_field = "dispatched_at"
    # An ORM ordering, not a ``?sort`` token.
    default_sort = "-dispatched_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_get_dispatch_challans",
        summary="List dispatch challans (filter by client / destination city, sortable)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="required",
        ),
        responses={200: DispatchChallanPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return challan_queryset()

    def serialize_page(
        self, page_items: list[DispatchEntry], request: Request
    ) -> list[dict]:
        return [challan_entry_payload(entry) for entry in page_items]
