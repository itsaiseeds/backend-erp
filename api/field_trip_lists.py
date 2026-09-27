"""Filters and sorts for the field-trip list endpoints, shared by both clients.

The sales-admin and Android lists accept the same query contract and differ
only in *scope* -- every trip versus the caller's own -- so each view builds
its filters from :func:`field_trip_filters` with its own scope, and the option
lists a picker shows are drawn from that same scope: a sales person never sees
another sales person's city in their picker.

The farmer-visit lists are always scoped to one trip, named in the path; the
views 404 an unknown (or, on Android, somebody else's) trip before any option
list is built, so the options here only need the trip's public id.
"""

from __future__ import annotations

from collections.abc import Callable

from django.db.models import Exists, OuterRef, QuerySet
from rest_framework import serializers
from rest_framework.request import Request

from aggregator.models import FarmerVisitCrop, FarmerVisitProduct, FieldTrip
from aggregator.models.Status import StatusIds
from common.views.paginated_date_range import (
    ListFilter,
    QuerysetFilter,
    RangeFilter,
    SortOption,
    parse_datetime,
    parse_int,
    parse_str,
)

FIELD_TRIP_STATUS_CODES = [status.name for status in StatusIds.field_trip_statuses()]

TripScope = Callable[[Request], QuerySet[FieldTrip]]


def _parse_status(raw: str) -> str:
    code = parse_str(raw).upper()
    if code not in FIELD_TRIP_STATUS_CODES:
        raise serializers.ValidationError(
            f"Unknown status '{raw}'. Allowed: {', '.join(FIELD_TRIP_STATUS_CODES)}."
        )
    return code


def _parse_yes_no(raw: str) -> bool:
    value = parse_str(raw).lower()
    if value in ("true", "yes", "1"):
        return True
    if value in ("false", "no", "0"):
        return False
    raise serializers.ValidationError(f"'{raw}' is not true or false.")


def field_trip_filters(scope: TripScope, *, by_sales_person: bool) -> tuple[ListFilter, ...]:
    """The trip-list filters, with option lists drawn from ``scope(request)``.

    ``by_sales_person`` adds the ``created_by`` filter -- meaningful only to a
    sales admin, since a sales person's list is theirs alone.
    """

    def sales_people(request: Request) -> list[dict]:
        rows = (
            scope(request)
            .values_list("created_by_id", "created_by__name")
            .distinct()
            .order_by("created_by__name")
        )
        return [{"value": user_id, "label": name} for user_id, name in rows]

    def cities(request: Request) -> list[dict]:
        rows = scope(request).values_list("city_id", "city__name").distinct().order_by("city__name")
        return [{"value": city_id, "label": name} for city_id, name in rows]

    filters: list[ListFilter] = []
    if by_sales_person:
        filters.append(
            QuerysetFilter(
                "created_by",
                label="Sales Person",
                lookup="created_by_id__in",
                parse=parse_int,
                description="User id(s) of the sales person on the trip (see options).",
                options=sales_people,
            )
        )
    filters += [
        QuerysetFilter(
            "status",
            label="Status",
            parse=_parse_status,
            apply=lambda queryset, codes: queryset.filter(status__code__in=codes),
            description="Field-trip lifecycle status.",
            options=[
                {"value": code, "label": code.replace("_", " ").title()}
                for code in FIELD_TRIP_STATUS_CODES
            ],
        ),
        QuerysetFilter(
            "city_id",
            label="City",
            lookup="city_id__in",
            parse=parse_int,
            description="City id(s) the trip goes to (see options).",
            options=cities,
        ),
        QuerysetFilter(
            "village",
            label="Village",
            lookup="village__icontains",
            parse=parse_str,
            multi=False,
            description="Case-insensitive substring of the village name.",
        ),
        RangeFilter(
            "expected_start",
            label="Expected Start",
            field="expected_start_at",
            parse=parse_datetime,
            suffixes=("gte", "lte"),
            description="When the trip is planned to start (inclusive bounds).",
        ),
    ]
    return tuple(filters)


FIELD_TRIP_SORTS = (
    SortOption(
        "expected_start_at",
        label="Expected Start",
        description="When the trip is planned to start (default: latest first).",
    ),
    SortOption(
        "created_at",
        label="Created",
        description="When the trip was planned.",
    ),
)


def _path_trip_public_id(request: Request) -> str:
    """The trip named in the URL of the farmer-visit list being served."""
    return request.parser_context["kwargs"]["public_id"]


def _trip_crops(request: Request) -> list[dict]:
    rows = (
        FarmerVisitCrop.objects.filter(
            farmer_visit__field_trip__public_id=_path_trip_public_id(request),
            farmer_visit__is_deleted=False,
        )
        .values_list("crop_id", "crop__name")
        .distinct()
        .order_by("crop__name")
    )
    return [{"value": crop_id, "label": name} for crop_id, name in rows]


def _trip_products(request: Request) -> list[dict]:
    rows = (
        FarmerVisitProduct.objects.filter(
            farmer_visit__field_trip__public_id=_path_trip_public_id(request),
            farmer_visit__is_deleted=False,
        )
        .values_list("product__public_id", "product__name")
        .distinct()
        .order_by("product__name")
    )
    return [{"value": public_id, "label": name} for public_id, name in rows]


def _by_crop(queryset: QuerySet, crop_ids: list[int]) -> QuerySet:
    return queryset.filter(
        Exists(FarmerVisitCrop.objects.filter(farmer_visit=OuterRef("pk"), crop_id__in=crop_ids))
    )


def _by_product(queryset: QuerySet, public_ids: list[str]) -> QuerySet:
    return queryset.filter(
        Exists(
            FarmerVisitProduct.objects.filter(
                farmer_visit=OuterRef("pk"), product__public_id__in=public_ids
            )
        )
    )


def _by_product_use(queryset: QuerySet, values: list[bool]) -> QuerySet:
    uses = Exists(FarmerVisitProduct.objects.filter(farmer_visit=OuterRef("pk")))
    return queryset.filter(uses) if values[0] else queryset.exclude(uses)


FARMER_VISIT_FILTERS: tuple[ListFilter, ...] = (
    QuerysetFilter(
        "crop",
        label="Crop",
        parse=parse_int,
        apply=_by_crop,
        description="Crop id(s) the farmer grows (see options).",
        options=_trip_crops,
    ),
    QuerysetFilter(
        "product",
        label="Product",
        parse=parse_str,
        apply=_by_product,
        description="Product public id(s) the farmer uses (see options).",
        options=_trip_products,
    ),
    QuerysetFilter(
        "uses_our_products",
        label="Uses Our Products",
        parse=_parse_yes_no,
        multi=False,
        apply=_by_product_use,
        description="true: farmers using at least one of our products; false: none.",
        options=[{"value": "true", "label": "Yes"}, {"value": "false", "label": "No"}],
    ),
)

FARMER_VISIT_SORTS = (
    SortOption(
        "created_at",
        label="Recorded",
        description="When the farmer was recorded (default: latest first).",
    ),
    SortOption(
        "land_area",
        label="Land Area",
        fields=("land_area_bigha",),
        description="Land held, smallest first.",
    ),
    SortOption(
        "farmer_name",
        label="Farmer Name",
        description="Farmer name, A->Z.",
    ),
)
