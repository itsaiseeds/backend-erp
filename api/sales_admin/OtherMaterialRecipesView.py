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

from django.db import transaction
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import recipe_payload
from aggregator.models import OtherMaterialRecipe
from aggregator.ProductOperations import assert_products_usable
from api.inward_serializers import (
    RECIPE_QUERYSET_FILTERS,
    RECIPE_SORT_OPTIONS,
    CreateRecipeSerializer,
    RecipeListPageSerializer,
    RecipePayloadSerializer,
)
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    list_query_parameters,
    query_flag,
)


class OtherMaterialRecipesView(AdminPaginatedDateRangeListView):
    """List (GET) or create (POST) other material recipes (app admin only)."""

    serializer_class = CreateRecipeSerializer
    enforce_date_range_filters = False
    default_sort = ("product__name", "packet_weight", "pk")
    queryset_filters = RECIPE_QUERYSET_FILTERS
    sort_options = RECIPE_SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_other_material_recipes_list",
        summary="List other material recipes (filter by product / material type, sortable)",
        parameters=list_query_parameters(
            queryset_filters=RECIPE_QUERYSET_FILTERS,
            sort_options=RECIPE_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: RecipeListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        recipes = OtherMaterialRecipe.objects.select_related("product", "material_type")
        if query_flag(request, "all"):
            # ``?all=true`` is the picker the inward booking form uses; a frozen
            # product cannot be booked, so it is not offered. The paginated
            # management list keeps showing it.
            recipes = recipes.filter(product__is_usable=True)
        return recipes

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
        with transaction.atomic():
            assert_products_usable([data["product"]], action="get a recipe")
            recipe = OtherMaterialRecipe.objects.create(
                product=data["product"],
                material_type=data["material_type"],
                packet_weight=data["packet_weight"],
                quantity=data["quantity"],
                created_by=request.user,
            )
        return Response(recipe_payload(recipe), status=status.HTTP_201_CREATED)
