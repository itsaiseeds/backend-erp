"""Inward raw material endpoint: ``GET``/``POST`` ``/api/sales-admin/inward-raw-materials``.

Only an application Admin may view or create lots (``admin_required``). A lot
records raw-material replenishment: how many kilograms of a ``Product`` came in
from a ``Party``, when it was sampled for the lab, and its ``status``. The
entry's date is its ``created_at``; ``effective_date`` is **not** accepted here
-- flipping ``status`` to ``In Use`` with ``PATCH`` stamps it with today (see
``UpdateInwardRawMaterialView``), so a freshly booked lot never counts toward
stock by accident.

Every lot is exposed by its ``public_id`` (``IR-…``); the primary key is never
sent out.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import inward_raw_material_payload
from aggregator.models import InwardRawMaterial, InwardRawMaterialStatus, Party, Product
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
    parse_str,
)


class InwardRawMaterialProductRefSerializer(serializers.Serializer):
    """Output shape for the ``product`` reference on a lot."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class InwardRawMaterialPartyRefSerializer(serializers.Serializer):
    """Output shape for the ``party`` reference on a lot."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class InwardRawMaterialPayloadSerializer(serializers.Serializer):
    """Output shape for one raw-material lot."""

    public_id = serializers.CharField()
    product = InwardRawMaterialProductRefSerializer()
    party = InwardRawMaterialPartyRefSerializer()
    quantity_kg = serializers.CharField(help_text="Kilograms received.")
    status = serializers.CharField()
    lab_sampling_date = serializers.DateField(allow_null=True)
    effective_date = serializers.DateField(allow_null=True)


class CreateInwardRawMaterialSerializer(serializers.Serializer):
    """Request validation for booking a new raw-material lot.

    ``status`` is not accepted: every lot starts ``Lab Testing`` and is moved to
    ``In Use`` later with ``PATCH``. ``effective_date`` is stamped (today) at
    that flip and is deliberately absent here.
    """

    product = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Product.objects.all(),
        error_messages={"required": "Product is required."},
    )
    party = serializers.PrimaryKeyRelatedField(
        queryset=Party.objects.all(),
        error_messages={"required": "Party is required."},
    )
    quantity_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Quantity in kg is required."},
        help_text="Kilograms received from the party.",
    )
    lab_sampling_date = serializers.DateField(required=False, allow_null=True)


class InwardRawMaterialListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = InwardRawMaterialPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "product",
        label="Product",
        lookup="product__public_id__in",
        parse=parse_str,
        description="Product public id(s).",
    ),
    QuerysetFilter(
        "party",
        label="Party",
        lookup="party_id__in",
        description="Party id(s).",
    ),
    QuerysetFilter(
        "status",
        label="Status",
        parse=parse_str,
        description="Lot status (Lab Testing / In Use).",
        options=[
            {"value": s.value, "label": s.label}
            for s in InwardRawMaterialStatus
        ],
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the lot was booked (default: newest first).",
    ),
    SortOption(
        "product",
        label="Product",
        fields=("product__name",),
        description="Product name, A->Z.",
    ),
    SortOption(
        "effective_date",
        label="Effective Date",
        fields=("effective_date",),
        description="Soonest effective date first (undated lots last).",
    ),
)


class InwardRawMaterialsView(AdminPaginatedDateRangeListView):
    """List (GET) or create (POST) inward raw-material lots (app admin only)."""

    serializer_class = CreateInwardRawMaterialSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_inward_raw_materials_list",
        summary="List inward raw-material lots (filter by product / party / status, sortable)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: InwardRawMaterialListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return InwardRawMaterial.objects.select_related("product", "party")

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [inward_raw_material_payload(entry) for entry in page_items]

    @extend_schema(
        summary="Create an inward raw-material lot",
        request=CreateInwardRawMaterialSerializer,
        responses={201: InwardRawMaterialPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateInwardRawMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry = InwardRawMaterial.objects.create(
            product=data["product"],
            party=data["party"],
            quantity_kg=data["quantity_kg"],
            lab_sampling_date=data.get("lab_sampling_date"),
            created_by=request.user,
        )
        return Response(inward_raw_material_payload(entry), status=status.HTTP_201_CREATED)
