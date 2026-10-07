"""Non-stock inward endpoint: ``GET``/``POST`` ``/api/sales-admin/non-stock-inwards``.

A standalone register of incoming consumables that are not seed stock --
pesticides, insecticides, spare parts, ... (``NonStockInward``). Deliberately
linked to nothing: no product, party or stock ledger, and never counted in any
stock figure.

Any application Admin may list entries (``admin_required``); recording,
editing (``PATCH``) and deleting (``DELETE``, see ``UpdateNonStockInwardView``)
need the same gate as booking inward material -- a superuser or an admin
holding ``Admin.can_update_stock_count`` (``assert_can_change_inward``).

Every entry is exposed by its ``public_id`` (``NS-…``); the primary key is
never sent out.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import assert_can_change_inward
from aggregator.models import NonStockInward, NonStockUnit
from api.inward_serializers import InwardCreatedByRefSerializer
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_str,
    public_id_filter,
)


def non_stock_inward_payload(entry: NonStockInward) -> dict:
    """Frontend-facing dict for one ``NonStockInward`` entry (``NS-…``)."""
    created_by = entry.created_by
    return {
        "public_id": entry.public_id,
        "name": entry.name,
        "description": entry.description,
        "company_name": entry.company_name,
        "price": str(entry.price) if entry.price is not None else None,
        "quantity": str(entry.quantity),
        "unit": entry.unit,
        "created_at": entry.created_at.isoformat(),
        "created_by": (
            {"id": created_by.id, "name": created_by.display_name}
            if created_by is not None
            else None
        ),
    }


class NonStockInwardPayloadSerializer(serializers.Serializer):
    """Output shape for one non-stock inward entry."""

    public_id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    company_name = serializers.CharField(allow_blank=True)
    price = serializers.CharField(allow_null=True, help_text="Null when not given.")
    quantity = serializers.CharField(help_text="Amount received, in ``unit``.")
    unit = serializers.ChoiceField(choices=NonStockUnit.choices)
    created_at = serializers.DateTimeField(help_text="When the entry was recorded.")
    created_by = InwardCreatedByRefSerializer(allow_null=True)


class NonStockInwardFieldsSerializer(serializers.Serializer):
    """The writable fields of a ``NonStockInward``, shared by create and update.

    ``description`` / ``company_name`` are optional free text (blank or null
    clears them); ``price`` is optional (null clears it) and never negative;
    ``quantity`` must be above zero.
    """

    name = serializers.CharField(
        max_length=255,
        error_messages={"required": "Name is required.", "blank": "Name is required."},
    )
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=""
    )
    company_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, allow_null=True, default=""
    )
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
        default=None,
    )
    quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Quantity is required."},
        help_text="Amount received, in ``unit``.",
    )
    unit = serializers.ChoiceField(
        choices=NonStockUnit.choices,
        error_messages={"required": "Unit is required."},
        help_text="Unit of measure for ``quantity``.",
    )

    def validate_description(self, value: str | None) -> str:
        return value or ""

    def validate_company_name(self, value: str | None) -> str:
        return (value or "").strip()

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value


class NonStockInwardListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = NonStockInwardPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


_QUERYSET_FILTERS = (
    public_id_filter("NS-"),
    QuerysetFilter(
        "name",
        label="Name",
        lookup="name__icontains",
        parse=parse_str,
        multi=False,
        description="Case-insensitive substring of the name.",
    ),
    QuerysetFilter(
        "company_name",
        label="Company Name",
        lookup="company_name__icontains",
        parse=parse_str,
        multi=False,
        description="Case-insensitive substring of the company name.",
    ),
    QuerysetFilter(
        "unit",
        label="Unit",
        lookup="unit__in",
        parse=parse_str,
        description="Unit(s) of measure (see options).",
        options=[{"value": unit.value, "label": unit.label} for unit in NonStockUnit],
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the entry was recorded (default: newest first).",
    ),
    SortOption("name", label="Name", fields=("name",), description="Name, A->Z."),
)


class NonStockInwardsView(AdminPaginatedDateRangeListView):
    """List (GET, any app admin) or record (POST, stock admins) non-stock inwards."""

    serializer_class = NonStockInwardFieldsSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_non_stock_inwards_list",
        summary="List non-stock inward entries (filter by name / company / unit, sortable)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: NonStockInwardListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return NonStockInward.objects.select_related("created_by")

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [non_stock_inward_payload(entry) for entry in page_items]

    @extend_schema(
        summary="Record a non-stock inward entry",
        request=NonStockInwardFieldsSerializer,
        responses={201: NonStockInwardPayloadSerializer},
    )
    def post(self, request):
        assert_can_change_inward(request.user)
        serializer = NonStockInwardFieldsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = NonStockInward.objects.create(
            **serializer.validated_data, created_by=request.user
        )
        return Response(non_stock_inward_payload(entry), status=status.HTTP_201_CREATED)
