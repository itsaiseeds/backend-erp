"""Product catalogue endpoint: ``GET /android/api/v1/sales-person-catalogue``.

The shelf a sales person picks from when booking an order: every sealed bag
(``ProductPackaging``) on offer, each carrying the product card the app renders
-- crop, stage, image and the marketing bullets -- so browsing costs one call.

The catalogue is global, not scoped to the caller: every sales person sells the
same catalogue.

Paginated, filterable and sortable through ``AndroidPaginatedDateRangeListView``:

* ``?crop=<id,...>`` -- bags of products of those crops. The ``available_filters``
  entry lists the eligible ``{value, label}`` crops (only the ones that actually
  have bags), so the picker needs no second call.
* ``?product=<P-...,...>`` -- bags of those products, by product public id.
* ``?stage=<CODE,...>`` -- ``BREEDER`` / ``FOUNDATION`` / ``RESEARCH`` /
  ``CERTIFICATE``; the entry carries all four as options.
* ``?name=<term>`` -- case-insensitive substring of the product name.
* ``?price_gte=`` / ``?price_lte=`` -- inclusive bounds on the bag's selling
  price (send either or both).
* ``?sort=<-?name,...>`` over ``price`` / ``stage`` / ``name``; ``stage``
  ascending runs breeder -> certificate. Default is product name, A->Z.

A bare request returns the first page of the whole catalogue.
"""

from __future__ import annotations

from django.db.models import Prefetch, QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.models import Crop, ProductDescriptionItem, ProductPackaging
from aggregator.models.Stage import StageIds
from aggregator.ProductOperations import catalogue_packaging_payload
from android.api.paginated_views import AndroidPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    RangeFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_decimal,
    parse_int,
    parse_str,
)

_STAGE_CODES = [stage.name for stage in StageIds]


class CatalogueStageSerializer(serializers.Serializer):
    """Output shape for the ``stage`` reference on a catalogue row."""

    code = serializers.CharField()
    name = serializers.CharField()
    sequence = serializers.IntegerField()


class CatalogueProductSerializer(serializers.Serializer):
    """Output shape for the product card on a catalogue row (schema only)."""

    public_id = serializers.CharField()
    name = serializers.CharField()
    crop = serializers.CharField(allow_null=True)
    stage = CatalogueStageSerializer()
    image_url = serializers.CharField(allow_blank=True)
    description_items = serializers.ListField(child=serializers.CharField())


class CatalogueItemSerializer(serializers.Serializer):
    """Output shape for one catalogue row -- a bag (schema only)."""

    public_id = serializers.CharField(
        help_text="Send this as product_packaging_public_id when creating an order."
    )
    name = serializers.CharField()
    packets = serializers.IntegerField(help_text="Packets in one bag.")
    packet_weight = serializers.CharField(help_text="Weight of one packet, in kg.")
    total_weight = serializers.CharField(help_text="Weight of the whole bag, in kg.")
    selling_price = serializers.CharField(help_text="Price of the whole bag.")
    product = CatalogueProductSerializer()


class CataloguePageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = CatalogueItemSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


def _crops_with_packagings(request: Request) -> list[dict]:
    """The distinct crops that actually have a bag on the shelf.

    This is the eligible value set for the ``crop`` filter: the picker never
    needs to offer a crop that would return an empty page. ``is_deleted=False``
    is explicit on both spans because a lookup across a relation does not pick
    up the soft-delete default manager.
    """
    rows = (
        Crop.objects.filter(
            products__is_deleted=False,
            products__packagings__is_deleted=False,
        )
        .values_list("id", "name")
        .distinct()
        .order_by("name")
    )
    return [{"value": crop_id, "label": name} for crop_id, name in rows]


def _parse_stage(raw: str) -> str:
    code = parse_str(raw).upper()
    if code not in _STAGE_CODES:
        raise serializers.ValidationError(
            f"Unknown stage '{raw}'. Allowed: {', '.join(_STAGE_CODES)}."
        )
    return code


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "crop",
        label="Crop",
        lookup="product__crop_id__in",
        parse=parse_int,
        description="Crop id(s) of the product (see options).",
        options=_crops_with_packagings,
    ),
    QuerysetFilter(
        "product",
        label="Product",
        lookup="product__public_id__in",
        parse=parse_str,
        description="Product public id(s), e.g. P-E79QA0E2OIHF.",
    ),
    QuerysetFilter(
        "stage",
        label="Stage",
        lookup="product__stage__code__in",
        parse=_parse_stage,
        description="Seed stage of the product.",
        options=[{"value": code, "label": code.capitalize()} for code in _STAGE_CODES],
    ),
    QuerysetFilter(
        "name",
        label="Name",
        lookup="product__name__icontains",
        parse=parse_str,
        multi=False,
        description="Case-insensitive substring of the product name.",
    ),
    RangeFilter(
        "price",
        label="Price",
        field="selling_price",
        parse=parse_decimal,
        suffixes=("gte", "lte"),
        description="Price of the whole bag (inclusive bounds).",
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "price",
        label="Price",
        fields=("selling_price",),
        description="Price of the whole bag, cheapest first.",
    ),
    SortOption(
        "stage",
        label="Stage",
        fields=("product__stage__sequence",),
        description="Seed stage; ascending runs breeder -> certificate.",
    ),
    SortOption(
        "name",
        label="Name",
        fields=("product__name",),
        description="Product name, A->Z (default).",
    ),
)


class SalesPersonCatalogueView(AndroidPaginatedDateRangeListView):
    """The bags a sales person can book: filter by crop / product / stage / name
    / price, sort by price / stage / name."""

    enforce_date_range_filters = False
    default_sort = ("product__name", "packet_weight")
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_sales_person_catalogue_list",
        summary=(
            "Browse the product catalogue "
            "(filter by crop / product / stage / name / price, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: CataloguePageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return ProductPackaging.objects.select_related(
            "product", "product__crop", "product__stage"
        ).prefetch_related(
            Prefetch(
                "product__description_items",
                queryset=ProductDescriptionItem.objects.order_by("sequence", "pk"),
            )
        )

    def serialize_page(
        self, page_items: list[ProductPackaging], request: Request
    ) -> list[dict]:
        return [catalogue_packaging_payload(item) for item in page_items]
