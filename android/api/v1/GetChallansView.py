"""My dispatch challans: ``GET /android/api/v1/get-challans``.

The Android counterpart of the admin website's ``dispatch-challans`` list, for a
sales person, returning the same challan rows (``challan_entry_payload``): our
consignor block, the consignee as it stood at dispatch, the HSN code, the
financial year, the journey and every lot-numbered line.

**Only the caller's own.** A sales person sees the challans of orders *they
created* (``Order.created_by``), and only while the order is still DISPATCHED or
DELIVERED -- the same rule the website applies (``challan_entries``). Nothing
belonging to anyone else is ever returned, and neither are the filter options:
every picker offers only clients and cities from the caller's own challans. A
custom order never appears, since only an admin can create one.

As on the website, the **date window is required** -- a challan list is read for
a period -- and it filters on when the goods left (``dispatched_at``).

The website's own endpoint is untouched; this view only reuses its queryset and
response schemas.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.DispatchOperations import challan_entry_payload
from aggregator.models import DispatchEntry
from aggregator.models.Order import DISPATCH_REQUIRED_STATUS_CODES
from android.api.paginated_views import AndroidPaginatedDateRangeListView
from api.sales_admin.GetDispatchChallansView import (
    DispatchChallanItemSerializer,
    challan_entries,
    challan_queryset,
)
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_int,
    parse_str,
    public_id_filter,
)


def owned_challan_entries(user) -> QuerySet:
    """The website's challan rule, narrowed to challans of orders ``user`` created.

    It filters on ``order__created_by``, so a custom order's challan never
    matches: its entry has no ``order``, and only an admin can create one.
    """
    return challan_entries().filter(order__created_by=user)


def owned_challan_queryset(user) -> QuerySet:
    """:func:`owned_challan_entries` with every join the challan payload walks."""
    return challan_queryset().filter(order__created_by=user)


class ChallanPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = DispatchChallanItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _my_challan_clients(request: Request) -> list[dict]:
    """The distinct clients the caller has a challan for (public id, name)."""
    rows = (
        owned_challan_entries(request.user)
        .values_list("client__public_id", "client__company_name")
        .distinct()
        .order_by("client__company_name")
    )
    return [{"value": public_id, "label": name} for public_id, name in rows]


def _my_challan_cities(request: Request) -> list[dict]:
    """The distinct cities the caller's challans were sent to."""
    rows = (
        owned_challan_entries(request.user)
        .values_list("to_city_id", "to_city__name")
        .distinct()
        .order_by("to_city__name")
    )
    return [{"value": city_id, "label": name} for city_id, name in rows]


def _parse_status(raw: str) -> str:
    code = parse_str(raw).upper()
    if code not in DISPATCH_REQUIRED_STATUS_CODES:
        raise serializers.ValidationError(
            f"Unknown status '{raw}'. Allowed: {', '.join(DISPATCH_REQUIRED_STATUS_CODES)}."
        )
    return code


_QUERYSET_FILTERS = (
    public_id_filter("DE-"),
    QuerysetFilter(
        "client",
        label="Client",
        lookup="client__public_id__in",
        parse=parse_str,
        description="Client public id(s) the goods were consigned to (see options).",
        options=_my_challan_clients,
    ),
    QuerysetFilter(
        "city_id",
        label="Destination City",
        lookup="to_city_id__in",
        parse=parse_int,
        description="City id(s) the goods were sent to (see options).",
        options=_my_challan_cities,
    ),
    QuerysetFilter(
        "status",
        label="Order Status",
        parse=_parse_status,
        apply=lambda queryset, codes: queryset.filter(order__status__code__in=codes),
        description="Whether the order is still DISPATCHED or already DELIVERED.",
        options=[
            {"value": code, "label": code.title()}
            for code in DISPATCH_REQUIRED_STATUS_CODES
        ],
    ),
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
        description="When the order was booked.",
    ),
)


class GetChallansView(AndroidPaginatedDateRangeListView):
    """List the challans of the caller's dispatched or delivered orders."""

    date_field = "dispatched_at"
    # An ORM ordering, not a ``?sort`` token.
    default_sort = "-dispatched_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_get_challans_list",
        summary="List my dispatch challans (filter by client / city / status, sortable)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="required",
        ),
        responses={200: ChallanPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return owned_challan_queryset(request.user)

    def serialize_page(
        self, page_items: list[DispatchEntry], request: Request
    ) -> list[dict]:
        return [challan_entry_payload(entry) for entry in page_items]
