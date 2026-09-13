"""Order list endpoint: ``GET /api/sales-admin/orders/``.

The sales-admin counterpart of ``GET /android/api/v1/get-orders``. Same
pagination / filter / sort contract, but scoped to *every* order rather than the
caller's own, with an extra ``created_by`` filter to narrow to one sales
person's book, and a wider card: the admin screen shows the delivery address,
the transport agency, the bags on the order, who onboarded the client and who
approved the order.

Paginated, filterable and sortable through ``AdminPaginatedDateRangeListView``:

* ``?created_by=<id1,id2,...>`` -- orders booked by a given sales person. The
  ``available_filters`` entry lists the eligible ``{value, label}`` sales people
  (exactly the ones who have booked something), so the picker needs no second
  call.
* ``?client=<id1,id2,...>`` -- orders for a given client; the entry lists every
  client that has an order.
* ``?product=<id1,id2,...>`` -- orders carrying a line of those products.
* ``?city_id=<id1,id2,...>`` -- orders delivering to one of those cities.
* ``?status=<CODE,...>`` -- ``BOOKED`` / ``UNDER_REVIEW`` / ``CONFIRMED`` /
  ``DISPATCHED`` / ``DELIVERED`` / ``ON_HOLD`` / ``REJECTED``; the entry carries
  all seven as options.
* ``?sort=<-?name,...>`` over ``created_at`` / ``price``; default newest first.

``price`` sorts on the order's total (line price x quantity, summed). It is a
per-order subquery rather than an aggregate over the item join on purpose:
``?product=`` already joins the item rows, and a ``Sum`` over that join would
total only the *matching* lines instead of the whole order.

A bare request returns the first page of every order.
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

from aggregator.models import Order, OrderItem
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import order_list_payload
from api.order_serializers import (
    OrderCardPackagingSerializer,
    TransportAgencyRefSerializer,
)
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

ORDER_STATUS_CODES = [status.name for status in StatusIds.order_statuses()]

_TOTAL_PRICE_FIELD = DecimalField(max_digits=14, decimal_places=2)

# The order's own total, computed per order rather than over the item join, so
# it stays correct when ``?product=`` has already narrowed that join.
# ``output_field`` is explicit on both wrappers: without it the mixed-type
# multiplication cannot be resolved.
_TOTAL_PRICE = Coalesce(
    Subquery(
        OrderItem.objects.filter(order=OuterRef("pk"))
        .values("order")
        .annotate(total=Sum(F("negotiated_selling_price") * F("quantity")))
        .values("total")[:1],
        output_field=_TOTAL_PRICE_FIELD,
    ),
    Value(Decimal("0.00")),
    output_field=_TOTAL_PRICE_FIELD,
)


class AdminOrderListClientSerializer(serializers.Serializer):
    """Output shape for the ``client`` reference on an order card."""

    public_id = serializers.CharField()
    company_name = serializers.CharField()


class AdminOrderListCitySerializer(serializers.Serializer):
    """Output shape for the ``city`` reference on an order card."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class AdminOrderListItemSerializer(serializers.Serializer):
    """Output shape for one order card (schema only)."""

    public_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    status = serializers.CharField(allow_null=True)
    client = AdminOrderListClientSerializer()
    client_created_by = serializers.CharField(
        allow_null=True, help_text="Sales person who onboarded the client."
    )
    created_by = serializers.CharField(
        allow_null=True, help_text="Sales person who booked the order."
    )
    verified_by = serializers.CharField(
        allow_null=True,
        help_text="Sales admin who approved the order; null until verified.",
    )
    delivery_address = serializers.CharField()
    city = AdminOrderListCitySerializer(allow_null=True)
    transport_agency = TransportAgencyRefSerializer(allow_null=True)
    dispatch_mode = serializers.ChoiceField(choices=["AGENCY", "PRIVATE"])
    expected_delivery_date = serializers.DateField()
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField()
    item_count = serializers.IntegerField()
    packagings = OrderCardPackagingSerializer(many=True)


class AdminOrderListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = AdminOrderListItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _salespeople_with_orders(request: Request) -> list[dict]:
    """The distinct sales people who have booked an order.

    The eligible value set for the ``created_by`` filter: the picker only ever
    needs to show a sales person who actually has an order. ``created_by`` is
    nullable, so a null-created order contributes no option -- a "None" entry
    would be meaningless and un-sendable as a filter value.
    """
    rows = (
        Order.objects.filter(created_by__isnull=False)
        .values_list("created_by_id", "created_by__name")
        .distinct()
        .order_by("created_by__name")
    )
    return [{"value": user_id, "label": name} for user_id, name in rows]


def _clients_with_orders(request: Request) -> list[dict]:
    """Every distinct client that has an order."""
    rows = (
        Order.objects.values_list("client_id", "client__company_name")
        .distinct()
        .order_by("client__company_name")
    )
    return [{"value": client_id, "label": name} for client_id, name in rows]


def _products_on_orders(request: Request) -> list[dict]:
    """Every distinct product appearing on an order.

    ``order__is_deleted`` is explicit because a lookup that spans the relation
    does not pick up ``Order``'s default soft-delete manager.
    """
    rows = (
        OrderItem.objects.filter(order__is_deleted=False)
        .values_list(
            "product_packaging__product_id", "product_packaging__product__name"
        )
        .distinct()
        .order_by("product_packaging__product__name")
    )
    return [{"value": product_id, "label": name} for product_id, name in rows]


def _delivery_cities(request: Request) -> list[dict]:
    """Every distinct city an order is delivered to."""
    rows = (
        Order.objects.values_list(
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
    """Keep orders carrying at least one line of one of ``product_ids``.

    ``items__is_deleted=False`` is explicit because the span does not apply
    ``OrderItem``'s soft-delete manager. ``distinct()`` collapses the extra row
    an order gains per matching line.
    """
    return queryset.filter(
        items__is_deleted=False,
        items__product_packaging__product_id__in=product_ids,
    ).distinct()


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "created_by",
        label="Sales Person",
        lookup="created_by_id__in",
        parse=parse_int,
        description="User id(s) of the sales person who booked the order (see options).",
        options=_salespeople_with_orders,
    ),
    QuerysetFilter(
        "client",
        label="Client",
        lookup="client_id__in",
        parse=parse_int,
        description="Client id(s) the order was booked for (see options).",
        options=_clients_with_orders,
    ),
    QuerysetFilter(
        "product",
        label="Product",
        parse=parse_int,
        apply=_by_product,
        description="Product id(s) the order contains (see options).",
        options=_products_on_orders,
    ),
    QuerysetFilter(
        "city_id",
        label="City",
        lookup="delivery_address__city_id__in",
        parse=parse_int,
        description="City id(s) the order is delivered to (see options).",
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
        description="When the order was booked (default: newest first).",
    ),
    SortOption(
        "price",
        label="Price",
        fields=("total_price",),
        description="Order total, cheapest first.",
    ),
)


class GetOrdersView(AdminPaginatedDateRangeListView):
    """List every order: filter by sales person / client / product / city / status."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_get_orders_list",
        summary=(
            "List orders (filter by sales person / client / product / city / "
            "status, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: AdminOrderListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return (
            Order.objects.select_related(
                "status",
                "created_by",
                "verified_by",
                "client",
                "client__created_by",
                "transport_agency",
                "delivery_address__city",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related(
                        "product_packaging__product"
                    ),
                )
            )
            .annotate(total_price=_TOTAL_PRICE)
        )

    def serialize_page(self, page_items: list[Order], request: Request) -> list[dict]:
        return [
            {
                **order_list_payload(order),
                "created_by": order.created_by.name if order.created_by else None,
                "verified_by": order.verified_by.name if order.verified_by else None,
                "client_created_by": (
                    order.client.created_by.name if order.client.created_by else None
                ),
                "transport_agency": (
                    {"id": order.transport_agency.id, "name": order.transport_agency.name}
                    if order.transport_agency
                    else None
                ),
            }
            for order in page_items
        ]
