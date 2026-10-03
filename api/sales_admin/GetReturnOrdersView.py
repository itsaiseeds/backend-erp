"""Return list endpoint: ``GET /api/sales-admin/return-orders/``.

Every return, across all sales people, newest first. Paginated, filterable and
sortable through ``AdminPaginatedDateRangeListView``:

* ``?public_id=`` -- substring of the return's ``RET-…`` id.
* ``?status=<CODE,...>`` -- ``RETURN_PENDING`` / ``RETURN_ACCEPTED`` /
  ``RETURN_REJECTED``; the entry carries all three as options.
* ``?created_by=<id1,id2,...>`` -- returns raised by a given sales person; the
  entry lists the sales people who have raised one.
* ``?client=<id1,id2,...>`` -- returns against a given client's orders; the
  entry lists every client with a return.
* ``?product=<id1,id2,...>`` -- returns with a line of those products.
* ``?order=<ORD-...,...>`` -- returns against those orders, by order public id.
* ``?sort=<-?name,...>`` over ``created_at`` / ``value``; default newest first.

``value`` sorts on the return's total (price per packet x packets, summed). It is
a per-return subquery rather than an aggregate over the item join on purpose:
``?product=`` already joins the item rows, and a ``Sum`` over that join would
total only the *matching* lines instead of the whole return -- the same way
``GetOrdersView`` sorts by price.

A bare request returns the first page of every return.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import (
    DecimalField,
    F,
    OuterRef,
    Prefetch,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.models import ReturnOrder, ReturnOrderItem, StatusIds
from aggregator.ReturnOrderOperations import return_order_list_payload
from api.paginated_views import AdminPaginatedDateRangeListView
from api.return_order_serializers import ReturnOrderListItemSerializer
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

RETURN_STATUS_CODES = [status.name for status in StatusIds.return_statuses()]

_TOTAL_VALUE_FIELD = DecimalField(max_digits=14, decimal_places=2)

# The return's own total, computed per return rather than over the item join, so
# it stays correct when ``?product=`` has already narrowed that join.
_TOTAL_VALUE = Coalesce(
    Subquery(
        ReturnOrderItem.objects.filter(return_order=OuterRef("pk"))
        .values("return_order")
        .annotate(total=Sum(F("price_per_packet") * F("packets")))
        .values("total")[:1],
        output_field=_TOTAL_VALUE_FIELD,
    ),
    Value(Decimal("0.00")),
    output_field=_TOTAL_VALUE_FIELD,
)


class AdminReturnOrderListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = ReturnOrderListItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _salespeople_with_returns(request: Request) -> list[dict]:
    """The distinct sales people who have raised a return."""
    rows = (
        ReturnOrder.objects.filter(created_by__isnull=False)
        .values_list("created_by_id", "created_by__name")
        .distinct()
        .order_by("created_by__name")
    )
    return [{"value": user_id, "label": name} for user_id, name in rows]


def _clients_with_returns(request: Request) -> list[dict]:
    """Every distinct client that has a return."""
    rows = (
        ReturnOrder.objects.values_list("order__client_id", "order__client__company_name")
        .distinct()
        .order_by("order__client__company_name")
    )
    return [{"value": client_id, "label": name} for client_id, name in rows]


def _products_on_returns(request: Request) -> list[dict]:
    """Every distinct product appearing on a return.

    ``return_order__is_deleted`` is explicit because a lookup that spans the
    relation does not pick up ``ReturnOrder``'s default soft-delete manager.
    """
    rows = (
        ReturnOrderItem.objects.filter(return_order__is_deleted=False, product__is_usable=True)
        .values_list("product_id", "product__name")
        .distinct()
        .order_by("product__name")
    )
    return [{"value": product_id, "label": name} for product_id, name in rows]


def _parse_status(raw: str) -> str:
    code = parse_str(raw).upper()
    if code not in RETURN_STATUS_CODES:
        raise serializers.ValidationError(
            f"Unknown status '{raw}'. Allowed: {', '.join(RETURN_STATUS_CODES)}."
        )
    return code


def _by_product(queryset: QuerySet, product_ids: list[int]) -> QuerySet:
    """Keep returns carrying at least one line of one of ``product_ids``.

    ``items__is_deleted=False`` is explicit because the span does not apply
    ``ReturnOrderItem``'s soft-delete manager. ``distinct()`` collapses the extra
    row a return gains per matching line.
    """
    return queryset.filter(items__is_deleted=False, items__product_id__in=product_ids).distinct()


_QUERYSET_FILTERS = (
    public_id_filter("RET-"),
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
    QuerysetFilter(
        "created_by",
        label="Sales Person",
        lookup="created_by_id__in",
        parse=parse_int,
        description="User id(s) of the sales person who raised the return (see options).",
        options=_salespeople_with_returns,
    ),
    QuerysetFilter(
        "client",
        label="Client",
        lookup="order__client_id__in",
        parse=parse_int,
        description="Client id(s) whose order the return is against (see options).",
        options=_clients_with_returns,
    ),
    QuerysetFilter(
        "product",
        label="Product",
        parse=parse_int,
        apply=_by_product,
        description="Product id(s) the return contains (see options).",
        options=_products_on_returns,
    ),
    QuerysetFilter(
        "order",
        label="Order",
        lookup="order__public_id__in",
        parse=parse_str,
        description="Public id(s) of the order the return is against.",
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the return was raised (default: newest first).",
    ),
    SortOption(
        "value",
        label="Value",
        fields=("total_value",),
        description="Return total, cheapest first.",
    ),
)


class GetReturnOrdersView(AdminPaginatedDateRangeListView):
    """List every return: filter by status / sales person / client / product / order."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_get_return_orders_list",
        summary=(
            "List returns (filter by status / sales person / client / product / order, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: AdminReturnOrderListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return (
            ReturnOrder.objects.select_related(
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
            .annotate(total_value=_TOTAL_VALUE)
        )

    def serialize_page(self, page_items: list[ReturnOrder], request: Request) -> list[dict]:
        return [return_order_list_payload(ret) for ret in page_items]
