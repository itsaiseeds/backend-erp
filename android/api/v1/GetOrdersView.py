"""Order list endpoint: ``GET /android/api/v1/get-orders``.

Lists the orders the calling sales person booked, newest first, each as a
compact card (client, delivery city, totals and the products on it) so the app
can render the list without a second call.

Scoped to the caller: the queryset starts from ``created_by=request.user``, so
one sales person can never see another's orders -- no filter widens that.

Paginated, filterable and sortable through ``AndroidPaginatedDateRangeListView``:

* ``?client=<CL-...,...>`` -- orders booked for those clients, by client public
  id. The ``available_filters`` entry lists the eligible ``{value, label}``
  clients (exactly the ones the caller has orders for), so the picker needs no
  second call.
* ``?product=<P-...,...>`` -- orders containing at least one line of those
  products, by product public id; the entry lists the products the caller has
  actually sold.
* ``?city_id=<id,...>`` -- orders delivering to one of those cities; the entry
  lists the caller's own delivery cities.
* ``?status=<CODE,...>`` -- ``BOOKED`` / ``UNDER_REVIEW`` / ``CONFIRMED`` /
  ``DISPATCHED`` / ``DELIVERED`` / ``ON_HOLD`` / ``REJECTED``; the entry carries
  all seven as options.
* ``?sort=<-?name,...>`` over ``created_at`` / ``price``; default newest first.

``price`` sorts on the order's total (line price x quantity, summed). It is a
subquery rather than an aggregate over the item join on purpose: ``?product=``
already joins the item rows, and a ``Sum`` over that join would total only the
*matching* lines instead of the whole order.

A bare request returns the first page of all the caller's orders.
"""

from __future__ import annotations

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
from android.api.paginated_views import AndroidPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_int,
    parse_str,
)

_ORDER_STATUS_CODES = [status.name for status in StatusIds.order_statuses()]

# The order's own total, computed per order rather than over the item join, so
# it stays correct when ``?product=`` has already narrowed that join.
_TOTAL_PRICE = Coalesce(
    Subquery(
        OrderItem.objects.filter(order=OuterRef("pk"))
        .values("order")
        .annotate(total=Sum(F("negotiated_selling_price") * F("quantity")))
        .values("total")[:1]
    ),
    Value(0),
    output_field=DecimalField(max_digits=14, decimal_places=2),
)


class OrderListProductSerializer(serializers.Serializer):
    """Output shape for one product line summarized on an order card."""

    public_id = serializers.CharField()
    name = serializers.CharField()
    quantity = serializers.IntegerField()


class OrderListClientSerializer(serializers.Serializer):
    """Output shape for the ``client`` reference on an order card."""

    public_id = serializers.CharField()
    company_name = serializers.CharField()


class OrderListCitySerializer(serializers.Serializer):
    """Output shape for the ``city`` reference on an order card."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class OrderListItemSerializer(serializers.Serializer):
    """Output shape for one order card (schema only)."""

    public_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    status = serializers.CharField(allow_null=True)
    client = OrderListClientSerializer()
    delivery_address = serializers.CharField()
    city = OrderListCitySerializer(allow_null=True)
    expected_delivery_date = serializers.DateField()
    dispatch_mode = serializers.CharField()
    total_amount = serializers.CharField()
    total_packets = serializers.IntegerField()
    item_count = serializers.IntegerField()
    products = OrderListProductSerializer(many=True)


class OrderListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = OrderListItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _my_order_clients(request: Request) -> list[dict]:
    """The distinct clients the caller has booked orders for.

    The eligible value set for ``?client=``: the picker only ever shows a
    client this sales person actually has an order with.
    """
    rows = (
        Order.objects.filter(created_by=request.user)
        .values_list("client__public_id", "client__company_name")
        .distinct()
        .order_by("client__company_name")
    )
    return [{"value": public_id, "label": name} for public_id, name in rows]


def _my_order_products(request: Request) -> list[dict]:
    """The distinct products on the caller's orders.

    ``order__is_deleted`` is explicit because a lookup that spans the relation
    does not pick up ``Order``'s default soft-delete manager.
    """
    rows = (
        OrderItem.objects.filter(order__created_by=request.user, order__is_deleted=False)
        .values_list(
            "product_packaging__product__public_id",
            "product_packaging__product__name",
        )
        .distinct()
        .order_by("product_packaging__product__name")
    )
    return [{"value": public_id, "label": name} for public_id, name in rows]


def _my_order_cities(request: Request) -> list[dict]:
    """The distinct delivery cities among the caller's orders."""
    rows = (
        Order.objects.filter(created_by=request.user)
        .values_list("delivery_address__city_id", "delivery_address__city__name")
        .distinct()
        .order_by("delivery_address__city__name")
    )
    return [{"value": city_id, "label": name} for city_id, name in rows]


def _parse_status(raw: str) -> str:
    code = parse_str(raw).upper()
    if code not in _ORDER_STATUS_CODES:
        raise serializers.ValidationError(
            f"Unknown status '{raw}'. Allowed: {', '.join(_ORDER_STATUS_CODES)}."
        )
    return code


def _by_product(queryset: QuerySet, public_ids: list[str]) -> QuerySet:
    """Keep orders carrying at least one line of one of ``public_ids``.

    ``items__is_deleted=False`` is explicit for the same reason as above: the
    span does not apply ``OrderItem``'s soft-delete manager. ``distinct()``
    collapses the row an order gains per matching line.
    """
    return queryset.filter(
        items__is_deleted=False,
        items__product_packaging__product__public_id__in=public_ids,
    ).distinct()


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "client",
        label="Client",
        lookup="client__public_id__in",
        parse=parse_str,
        description="Client public id(s) the order was booked for (see options).",
        options=_my_order_clients,
    ),
    QuerysetFilter(
        "product",
        label="Product",
        parse=parse_str,
        apply=_by_product,
        description="Product public id(s) the order contains (see options).",
        options=_my_order_products,
    ),
    QuerysetFilter(
        "city_id",
        label="City",
        lookup="delivery_address__city_id__in",
        parse=parse_int,
        description="City id(s) the order is delivered to (see options).",
        options=_my_order_cities,
    ),
    QuerysetFilter(
        "status",
        label="Status",
        parse=_parse_status,
        apply=lambda queryset, codes: queryset.filter(status__code__in=codes),
        description="Order lifecycle status.",
        options=[
            {"value": code, "label": code.replace("_", " ").title()}
            for code in _ORDER_STATUS_CODES
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


class GetOrdersView(AndroidPaginatedDateRangeListView):
    """List the caller's orders: filter by client / product / city / status, sort."""

    enforce_date_range_filters = False
    default_sort = "-created_at"
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_get_orders_list",
        summary="List my orders (filter by client / product / city / status, sortable)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: OrderListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return (
            Order.objects.filter(created_by=request.user)
            .select_related("client", "status", "delivery_address__city")
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
        return [order_list_payload(order) for order in page_items]
