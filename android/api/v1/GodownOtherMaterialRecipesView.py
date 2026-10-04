"""Godown other-material recipes: ``GET`` ``/android/api/v1/godown/other-material-recipes``.

View-only: the Android counterpart of the list half of
``api.sales_admin.OtherMaterialRecipesView`` (recipes are master data, created
by admins). Also the recipe picker for booking other-material lots, via the
``?all=true`` pagination escape. Godown-manager token only.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.InwardOperations import recipe_payload
from aggregator.models import OtherMaterialRecipe
from android.api.paginated_views import AndroidGodownPaginatedDateRangeListView
from api.inward_serializers import (
    RECIPE_QUERYSET_FILTERS,
    RECIPE_SORT_OPTIONS,
    RecipeListPageSerializer,
)
from common.views.paginated_date_range import list_query_parameters


class GodownOtherMaterialRecipesView(AndroidGodownPaginatedDateRangeListView):
    """List other-material recipes (godown manager only)."""

    enforce_date_range_filters = False
    default_sort = ("product__name", "packet_weight", "pk")
    queryset_filters = RECIPE_QUERYSET_FILTERS
    sort_options = RECIPE_SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_godown_other_material_recipes_list",
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
        # A frozen product (``Product.is_usable`` false) is not shown on the material
        # side at all -- neither in the booking picker (``?all=true``) nor the list.
        return OtherMaterialRecipe.objects.filter(product__is_usable=True).select_related(
            "product", "material_type"
        )

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [recipe_payload(recipe) for recipe in page_items]
