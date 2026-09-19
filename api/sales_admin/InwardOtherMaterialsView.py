"""Inward other material endpoint: ``GET``/``POST`` ``/api/sales-admin/inward-other-materials``.

Only an application Admin may view or create lots (``admin_required``). A lot
records a packing-material delivery: how much of a recipe's material a
``Party`` supplied. ``quantity`` is measured in the recipe's material unit
(count / kg / litre -- see the recipe's ``material_type.unit_type``).

Like raw-material lots, ``effective_date`` is **not** accepted here; booking
stamps it with today, which is what starts the entry counting toward
``other-material-stock`` on the day it arrives.

Every lot is exposed by its ``public_id`` (``IO-…``); the primary key is never
sent out.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import (
    inward_other_material_payload,
    today,
)
from aggregator.models import InwardOtherMaterial, OtherMaterialRecipe, Party
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
)


class InwardOtherMaterialProductRefSerializer(serializers.Serializer):
    """Output shape for the ``product`` reference inside a recipe ref."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class InwardOtherMaterialRecipeRefSerializer(serializers.Serializer):
    """Output shape for the ``recipe`` reference on a lot."""

    public_id = serializers.CharField()
    product = InwardOtherMaterialProductRefSerializer()
    packet_weight = serializers.CharField(help_text="Weight of the covered packet, in kg.")


class InwardOtherMaterialPartyRefSerializer(serializers.Serializer):
    """Output shape for the ``party`` reference on a lot."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class InwardOtherMaterialPayloadSerializer(serializers.Serializer):
    """Output shape for one inward-other-material lot."""

    public_id = serializers.CharField()
    recipe = InwardOtherMaterialRecipeRefSerializer()
    party = InwardOtherMaterialPartyRefSerializer()
    quantity = serializers.CharField(help_text="Amount received, in the recipe's unit.")
    effective_date = serializers.DateField(allow_null=True)


class CreateInwardOtherMaterialSerializer(serializers.Serializer):
    """Request validation for booking a new other-material lot.

    ``effective_date`` is absent on purpose: booking stamps it with today
    (see ``InwardOtherMaterialsView.post``).
    """

    party = serializers.PrimaryKeyRelatedField(
        queryset=Party.objects.all(),
        error_messages={"required": "Party is required."},
    )
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=OtherMaterialRecipe.objects.all(),
        error_messages={"required": "Recipe is required."},
    )
    quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Quantity is required."},
        help_text="Amount received, in the recipe's material unit.",
    )

    def validate(self, attrs):
        if attrs["quantity"] <= 0:
            raise serializers.ValidationError(
                {"quantity": "Quantity must be greater than zero."}
            )
        return attrs


class InwardOtherMaterialListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = InwardOtherMaterialPayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "party",
        label="Party",
        lookup="party_id__in",
        description="Party id(s).",
    ),
    QuerysetFilter(
        "material_type",
        label="Material Type",
        lookup="recipe__material_type_id__in",
        description="Material type id(s) (see the recipe).",
    ),
    QuerysetFilter(
        "product",
        label="Product",
        lookup="recipe__product__public_id__in",
        description="Product public id(s) (see the recipe).",
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "created_at",
        label="Created",
        description="When the lot was booked (default: newest first).",
    ),
    SortOption(
        "party",
        label="Party",
        fields=("party__name",),
        description="Party name, A->Z.",
    ),
    SortOption(
        "effective_date",
        label="Effective Date",
        fields=("effective_date",),
        description="Soonest effective date first (undated lots last).",
    ),
)


class InwardOtherMaterialsView(AdminPaginatedDateRangeListView):
    """List (GET) or create (POST) inward other-material lots (app admin only)."""

    serializer_class = CreateInwardOtherMaterialSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_inward_other_materials_list",
        summary=(
            "List inward other-material lots (filter by party / material "
            "type / product, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: InwardOtherMaterialListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return InwardOtherMaterial.objects.select_related(
            "party", "recipe__product", "recipe__material_type"
        )

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [inward_other_material_payload(entry) for entry in page_items]

    @extend_schema(
        summary="Create an inward other-material lot",
        request=CreateInwardOtherMaterialSerializer,
        responses={201: InwardOtherMaterialPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateInwardOtherMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry = InwardOtherMaterial.objects.create(
            party=data["party"],
            recipe=data["recipe"],
            quantity=data["quantity"],
            effective_date=today(),
            created_by=request.user,
        )
        return Response(inward_other_material_payload(entry), status=status.HTTP_201_CREATED)
