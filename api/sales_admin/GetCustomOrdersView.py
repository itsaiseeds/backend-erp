"""Custom-order list endpoint: ``GET /api/sales-admin/custom-orders/``.

The custom-order counterpart of ``GET /api/sales-admin/orders/``: the same
pagination / filter / sort contract, over **every** custom order -- a sales
admin sees the ones every other sales admin booked, not only their own.

Paginated, filterable and sortable through ``AdminPaginatedDateRangeListView``:

* ``?created_by=<id1,id2,...>`` -- custom orders booked by a given sales admin.
  The ``available_filters`` entry lists the eligible ``{value, label}`` admins
  (exactly the ones who have booked one), so the picker needs no second call.
* ``?client=<id1,id2,...>`` -- custom orders for a given client; the entry
  lists every client that has one.
* ``?product=<id1,id2,...>`` -- custom orders carrying a line of those products.
* ``?city_id=<id1,id2,...>`` -- custom orders delivering to one of those cities.
* ``?status=<CODE,...>`` -- any order lifecycle status; the entry carries all
  seven as options, the same catalogue ``orders/`` has.
* ``?sort=<-?name,...>`` over ``created_at`` / ``price``; default newest first.

``price`` sorts on the custom order's total (per-packet price x packets,
summed), as a per-order subquery for the reason ``GetOrdersView`` gives:
``?product=`` already joins the item rows, and a ``Sum`` over that join would
total only the matching lines.

A bare request returns the first page of every custom order.
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

from aggregator.CustomOrderOperations import custom_order_list_payload
from aggregator.models import CustomOrder, CustomOrderItem
from aggregator.models.Status import StatusIds
from api.custom_order_serializers import CustomOrderListPageSerializer
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    QuerysetFilter,
    SortOption,
    list_query_parameters,
    parse_int,
    parse_str,
)

ORDER_STATUS_CODES = [status.name for status in StatusIds.order_statuses()]

_TOTAL_PRICE_FIELD = DecimalField(max_digits=14, decimal_places=2)

# The custom order's own total, computed per order rather than over the item
# join, so it stays correct when ``?product=`` has already narrowed that join.
_TOTAL_PRICE = Coalesce(
    Subquery(
        CustomOrderItem.objects.filter(custom_order=OuterRef("pk"))
        .values("custom_order")
        .annotate(total=Sum(F("negotiated_selling_price") * F("packets")))
        .values("total")[:1],
        output_field=_TOTAL_PRICE_FIELD,
    ),
    Value(Decimal("0.00")),
    output_field=_TOTAL_PRICE_FIELD,
)


def _admins_with_custom_orders(request: Request) -> list[dict]:
    """The distinct sales admins who have booked a custom order."""
    rows = (
        CustomOrder.objects.filter(created_by__isnull=False)
        .values_list("created_by_id", "created_by__name")
        .distinct()
        .order_by("created_by__name")
    )
    return [{"value": user_id, "label": name} for user_id, name in rows]


def _clients_with_custom_orders(request: Request) -> list[dict]:
    """Every distinct client that has a custom order."""
    rows = (
        CustomOrder.objects.values_list("client_id", "client__company_name")
        .distinct()
        .order_by("client__company_name")
    )
    return [{"value": client_id, "label": name} for client_id, name in rows]


def _products_on_custom_orders(request: Request) -> list[dict]:
    """Every distinct product appearing on a custom order.

    ``custom_order__is_deleted`` is explicit because a lookup that spans the
    relation does not pick up ``CustomOrder``'s default soft-delete manager.
    """
    rows = (
        CustomOrderItem.objects.filter(custom_order__is_deleted=False)
        .values_list("product_id", "product__name")
        .distinct()
        .order_by("product__name")
    )
    return [{"value": product_id, "label": name} for product_id, name in rows]


def _delivery_cities(request: Request) -> list[dict]:
    """Every distinct city a custom order is delivered to."""
    rows = (
        CustomOrder.objects.values_list(
            "delivery_address__city_id", "delivery_address__city__name"
        )
        .distinct()
        .order_by("delivery_address__city__name")
    )
    return [{"value": city_id, "label": name} for city_id, name in rows]


def _parse_status(raw: str) -> str:
    code = parse_str(raw).upper()
    if code not in ORDER_STATUS_CODES:
        raise serializers.ValidationError(
            f"Unknown status '{raw}'. Allowed: {', '.join(ORDER_STATUS_CODES)}."
        )
    return code


def _by_product(queryset: QuerySet, product_ids: list[int]) -> QuerySet:
    """Keep custom orders carrying at least one line of one of ``product_ids``.

    ``items__is_deleted=False`` is explicit because the span does not apply
    ``CustomOrderItem``'s soft-delete manager. ``distinct()`` collapses the
    extra row an order gains per matching line.
    """
    return queryset.filter(
        items__is_deleted=False, items__product_id__in=product_ids
    ).distinct()


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "created_by",
        label="Sales Admin",
        lookup="created_by_id__in",
        parse=parse_int,
        description="User id(s) of the sales admin who booked the custom order (see options).",
        options=_admins_with_custom_orders,
    ),
    QuerysetFilter(
        "client",
        label="Client",
        lookup="client_id__in",
        parse=parse_int,
        description="Client id(s) the custom order was booked for (see options).",
        options=_clients_with_custom_orders,
    ),
    QuerysetFilter(
        "product",
        label="Product",
        parse=parse_int,
        apply=_by_product,
        description="Product id(s) the custom order contains (see options).",
        options=_products_on_custom_orders,
    ),
    QuerysetFilter(
        "city_id",
        label="City",
        lookup="delivery_address__city_id__in",
        parse=parse_int,
        description="City id(s) the custom order is delivered to (see options).",
        options=_delivery_cities,
    ),
    QuerysetFilter(
        "status",
        label="Status",
        parse=_parse_status,
        apply=lambda queryset, codes: queryset.filter(status__code__in=codes),
        description="Order lifecycle status.",
        options=[
            {"value": code, "label": code.replace("_", " ").title()}
            for code in ORDER_STATUS_CODES
        ],
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the custom order was booked (default: newest first).",
    ),
    SortOption(
        "price",
        label="Price",
        fields=("total_price",),
        description="Custom order total, cheapest first.",
    ),
)


class GetCustomOrdersView(AdminPaginatedDateRangeListView):
    """List every custom order: filter by admin / client / product / city / status."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_get_custom_orders_list",
        summary=(
            "List custom orders (filter by sales admin / client / product / city / "
            "status, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: CustomOrderListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return (
            CustomOrder.objects.select_related(
                "status",
                "created_by",
                "verified_by",
                "client",
                "client__created_by",
                "delivery_address__city",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=CustomOrderItem.objects.select_related("product"),
                )
            )
            .annotate(total_price=_TOTAL_PRICE)
        )

    def serialize_page(
        self, page_items: list[CustomOrder], request: Request
    ) -> list[dict]:
        return [
            {
                **custom_order_list_payload(order),
                "created_by": order.created_by.name if order.created_by else None,
                "verified_by": order.verified_by.name if order.verified_by else None,
                "client_created_by": (
                    order.client.created_by.name if order.client.created_by else None
                ),
            }
            for order in page_items
        ]
