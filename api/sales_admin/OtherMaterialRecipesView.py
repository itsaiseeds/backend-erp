"""Other-material-recipe endpoint: ``GET``/``POST`` ``/api/sales-admin/other-material-recipes``.

Only an application Admin may view or create recipes (``admin_required``).
A recipe ties one material type to one product's packet weight -- how much of
the material one pack of that variant needs -- and is exposed by its ``public_id``
(``OMR-…``).

Recipes are **never edited in place**: changing one means soft-deleting the old
row and creating a fresh one, so ``InwardOtherMaterial`` entries keep pointing
at the version they were booked against. There is therefore no update verb here
(``PATCH`` is a 405); only create, list and delete (see
``DeleteOtherMaterialRecipeView``).
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import recipe_payload
from aggregator.models import OtherMaterialRecipe, OtherMaterialType, Product
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    FilterCatalogueEntrySerializer,
    QuerysetFilter,
    SortCatalogueEntrySerializer,
    SortOption,
    list_query_parameters,
)


class RecipeMaterialTypeRefSerializer(serializers.Serializer):
    """Output shape for the ``material_type`` reference on a recipe."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    unit_type = serializers.CharField()


class RecipeProductRefSerializer(serializers.Serializer):
    """Output shape for the ``product`` reference on a recipe."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class RecipePayloadSerializer(serializers.Serializer):
    """Output shape for one recipe row."""

    public_id = serializers.CharField()
    product = RecipeProductRefSerializer()
    material_type = RecipeMaterialTypeRefSerializer()
    packet_weight = serializers.CharField(help_text="Weight of the covered packet, in kg.")
    quantity = serializers.CharField(help_text="Amount per pack, in the material type's unit.")


class CreateRecipeSerializer(serializers.Serializer):
    """Request validation for creating a new ``OtherMaterialRecipe``."""

    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        error_messages={"required": "Product is required."},
    )
    material_type = serializers.PrimaryKeyRelatedField(
        queryset=OtherMaterialType.objects.all(),
        error_messages={"required": "Material type is required."},
    )
    packet_weight = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Packet weight is required."},
        help_text="Weight of the covered packet, in kilograms (the product variant).",
    )
    quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=0,
        error_messages={"required": "Quantity is required."},
        help_text=(
            "Multiples of the material per pack, in the material type's unit "
            "(2 leaflets, 2.000 kg cover, 5 litre)."
        ),
    )

    def validate(self, attrs):
        if attrs["packet_weight"] <= 0:
            raise serializers.ValidationError(
                {"packet_weight": "Packet weight must be greater than zero."}
            )
        if attrs["quantity"] <= 0:
            raise serializers.ValidationError(
                {"quantity": "Quantity must be greater than zero."}
            )
        qs = OtherMaterialRecipe.all_objects.filter(
            product=attrs["product"],
            material_type=attrs["material_type"],
            packet_weight=attrs["packet_weight"],
        )
        if qs.exists():
            raise serializers.ValidationError(
                "A recipe for this product, material type and packet weight "
                "already exists."
            )
        return attrs


class RecipeListPageSerializer(serializers.Serializer):
    """Output shape for the paginated envelope (schema only)."""

    total_count = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page_number = serializers.IntegerField(allow_null=True)
    previous_page_number = serializers.IntegerField(allow_null=True)
    results = RecipePayloadSerializer(many=True)
    available_filters = FilterCatalogueEntrySerializer(many=True)
    available_sorts = SortCatalogueEntrySerializer(many=True)


_QUERYSET_FILTERS = (
    QuerysetFilter(
        "product",
        label="Product",
        lookup="product__public_id__in",
        description="Product public id(s).",
    ),
    QuerysetFilter(
        "material_type",
        label="Material Type",
        lookup="material_type_id__in",
        description="Material type id(s).",
    ),
)
_SORT_OPTIONS = (
    SortOption(
        "product",
        label="Product",
        fields=("product__name",),
        description="Product name, A->Z (default).",
    ),
    SortOption(
        "packet_weight",
        label="Packet Weight",
        fields=("packet_weight",),
        description="Packet weight, lightest first.",
    ),
    SortOption(
        "created_at",
        label="Created",
        description="When the recipe was added.",
    ),
)


class OtherMaterialRecipesView(AdminPaginatedDateRangeListView):
    """List (GET) or create (POST) other material recipes (app admin only)."""

    serializer_class = CreateRecipeSerializer
    enforce_date_range_filters = False
    default_sort = ("product__name", "packet_weight", "pk")
    queryset_filters = _QUERYSET_FILTERS
    sort_options = _SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_other_material_recipes_list",
        summary="List other material recipes (filter by product / material type, sortable)",
        parameters=list_query_parameters(
            queryset_filters=_QUERYSET_FILTERS,
            sort_options=_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: RecipeListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return OtherMaterialRecipe.objects.select_related(
            "product", "material_type"
        )

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [recipe_payload(recipe) for recipe in page_items]

    @extend_schema(
        summary="Create an other material recipe",
        request=CreateRecipeSerializer,
        responses={201: RecipePayloadSerializer},
    )
    def post(self, request):
        serializer = CreateRecipeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        recipe = OtherMaterialRecipe.objects.create(
            product=data["product"],
            material_type=data["material_type"],
            packet_weight=data["packet_weight"],
            quantity=data["quantity"],
            created_by=request.user,
        )
        return Response(recipe_payload(recipe), status=status.HTTP_201_CREATED)
