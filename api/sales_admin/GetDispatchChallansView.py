"""Challan list endpoint: ``GET /api/sales-admin/dispatch-challans/``.

Every dispatched order whose challan is complete, each row carrying that
challan in full: our own consignor block, the consignee as it stood at dispatch
time, the HSN code, the financial year, the journey, and every line with its lot
number.

What makes a challan complete depends on **who carried the goods**, and it is the
one rule worth stating plainly:

* an **agency** dispatch is listed only once its ``lr_number`` is recorded. The
  transporter's consignment note is part of that challan, and it is issued after
  collection, so the challan is genuinely incomplete until it arrives.
* a **private**, own-vehicle dispatch is listed straight away. There is no
  transporter, so there is no note to wait for -- withholding it would be waiting
  for something that will never come.

Both also need the order to still **be** dispatched -- status DISPATCHED or
DELIVERED -- and to have a live ``dispatch_entry``, the challan record written at
dispatch. The two are not the same check: ``revert-dispatch`` rewinds the status
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
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.DispatchOperations import dispatch_challan_payload
from aggregator.models import DispatchEntryItem, Order
from aggregator.models.Order import DISPATCH_REQUIRED_STATUS_CODES
from api.order_serializers import ProductRefSerializer
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_int,
)

# What makes an order's challan complete. Declared once: the list view filters on
# it and the option providers below reuse it, so a picker can never offer a
# client or a city with nothing behind it.
#
# The status codes come from ``DISPATCH_REQUIRED_STATUS_CODES`` rather than being
# spelled out, so this list follows the enum if the lifecycle ever gains a
# post-dispatch status.
#
# ``dispatch_details`` null means a private dispatch -- an order that has been
# dispatched went one way or the other, so there is no third case to cover.
# ``is_deleted`` is explicit because a lookup spanning the relation does not pick
# up ``DispatchEntry``'s soft-delete manager.
CHALLAN_Q = Q(
    status__code__in=DISPATCH_REQUIRED_STATUS_CODES,
    dispatch_entry__isnull=False,
    dispatch_entry__is_deleted=False,
) & (
    Q(dispatch_details__isnull=True)  # private: no transporter, nothing to wait for
    | Q(dispatch_details__lr_number__gt="")  # agency: the LR has been recorded
)


def challan_orders() -> QuerySet:
    """Every order that currently has a complete challan."""
    return Order.objects.filter(CHALLAN_Q)


def challan_queryset() -> QuerySet:
    """:func:`challan_orders` with every join ``dispatch_challan_payload`` walks.

    The payload reads the receiver off the ``DispatchEntry`` snapshot, so it is
    the entry's own address and cities that are selected here, not the order's
    or the client's. Shared by the challan list and the dispatch-receipt export.
    """
    return challan_orders().select_related(
        "dispatch_details",
        "dispatch_entry",
        "dispatch_entry__client",
        "dispatch_entry__client_address__pincode",
        "dispatch_entry__client_address__city",
        "dispatch_entry__client_address__state",
        "dispatch_entry__client_address__country",
        "dispatch_entry__from_city",
        "dispatch_entry__to_city",
    ).prefetch_related(
        Prefetch(
            "dispatch_entry__items",
            queryset=DispatchEntryItem.objects.select_related(
                "product_packaging__product"
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
    lr_number = serializers.CharField()
    dispatch_date = serializers.DateField()
    is_private = serializers.BooleanField()
    vehicle_number = serializers.CharField()
    driver_name = serializers.CharField()
    driver_number = serializers.CharField()
    from_city = serializers.CharField()
    to_city = serializers.CharField()


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


class DispatchChallanPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = DispatchChallanItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _clients_with_challans(request: Request) -> list[dict]:
    """Every distinct client that has a challan -- the client picker's options."""
    rows = (
        challan_orders()
        .values_list("client_id", "client__company_name")
        .distinct()
        .order_by("client__company_name")
    )
    return [{"value": client_id, "label": name} for client_id, name in rows]


def _challan_destination_cities(request: Request) -> list[dict]:
    """Every distinct city a challan was sent to."""
    rows = (
        challan_orders()
        .values_list("dispatch_entry__to_city_id", "dispatch_entry__to_city__name")
        .distinct()
        .order_by("dispatch_entry__to_city__name")
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
        lookup="dispatch_entry__to_city_id__in",
        parse=parse_int,
        description="City id(s) the goods were sent to (see options).",
        options=_challan_destination_cities,
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "dispatch_date",
        label="Dispatch Date",
        fields=("dispatch_entry__dispatched_at",),
        description="When the goods left (default: newest first).",
    ),
    SortOption(
        "created_at",
        label="Order Created",
        description="When the order was booked.",
    ),
)


class GetDispatchChallansView(AdminPaginatedDateRangeListView):
    """List the delivery challans of dispatched orders whose LR is recorded."""

    date_field = "dispatch_entry__dispatched_at"
    # An ORM ordering, not a ``?sort`` token -- hence the spelled-out span.
    default_sort = "-dispatch_entry__dispatched_at"
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

    def serialize_page(self, page_items: list[Order], request: Request) -> list[dict]:
        return [dispatch_challan_payload(order) for order in page_items]
