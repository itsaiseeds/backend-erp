"""Return list endpoint: ``GET /android/api/v1/get-return-orders``.

Lists the returns the calling sales person raised, newest first. Scoped to the
caller: the queryset starts from ``created_by=request.user``, so one sales person
never sees another's returns -- no filter widens that.

Paginated, filterable and sortable through ``AndroidPaginatedDateRangeListView``:

* ``?status=<CODE,...>`` -- ``RETURN_PENDING`` / ``RETURN_ACCEPTED`` /
  ``RETURN_REJECTED``; the entry carries all three as options.
* ``?order=<ORD-...,...>`` -- returns against those orders, by order public id.
* ``?sort=<-?name,...>`` over ``created_at``; default newest first.

A bare request returns the first page of all the caller's returns.
"""

from __future__ import annotations

from django.db.models import Prefetch, QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.models import ReturnOrder, ReturnOrderItem, StatusIds
from aggregator.ReturnOrderOperations import return_order_list_payload
from android.api.paginated_views import AndroidPaginatedDateRangeListView
from api.return_order_serializers import ReturnOrderListItemSerializer
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_str,
    public_id_filter,
)

RETURN_STATUS_CODES = [status.name for status in StatusIds.return_statuses()]


class ReturnOrderListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = ReturnOrderListItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _parse_status(raw: str) -> str:
    code = parse_str(raw).upper()
    if code not in RETURN_STATUS_CODES:
        raise serializers.ValidationError(
            f"Unknown status '{raw}'. Allowed: {', '.join(RETURN_STATUS_CODES)}."
        )
    return code


_QUERYSET_FILTERS = (
    public_id_filter("RET-"),
    QuerysetFilter(
        "order",
        label="Order",
        lookup="order__public_id__in",
        parse=parse_str,
        description="Public id(s) of the order the return is against.",
    ),
    QuerysetFilter(
        "status",
        label="Status",
        parse=_parse_status,
        apply=lambda queryset, codes: queryset.filter(status__code__in=codes),
        description="Return lifecycle status.",
        options=[
            {"value": code, "label": code.removeprefix("RETURN_").title()}
            for code in RETURN_STATUS_CODES
        ],
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the return was raised (default: newest first).",
    ),
)


class GetReturnOrdersView(AndroidPaginatedDateRangeListView):
    """List the caller's own returns: filter by order / status, sort."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_get_return_orders_list",
        summary="List my returns (filter by order / status, sortable)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: ReturnOrderListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return (
            ReturnOrder.objects.filter(created_by=request.user)
            .select_related(
                "status",
                "order__status",
                "order__client",
                "created_by",
                "verified_by",
                "rejected_by",
            )
            .prefetch_related(
                Prefetch("items", queryset=ReturnOrderItem.objects.select_related("product"))
            )
        )

    def serialize_page(self, page_items: list[ReturnOrder], request: Request) -> list[dict]:
        return [return_order_list_payload(ret) for ret in page_items]
