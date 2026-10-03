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
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import (
    create_other_lot,
    inward_other_material_payload,
)
from aggregator.models import InwardOtherMaterial
from api.inward_serializers import (
    OTHER_LOT_QUERYSET_FILTERS,
    OTHER_LOT_SORT_OPTIONS,
    CreateInwardOtherMaterialSerializer,
    InwardOtherMaterialListPageSerializer,
    InwardOtherMaterialPayloadSerializer,
)
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    list_query_parameters,
)


class InwardOtherMaterialsView(AdminPaginatedDateRangeListView):
    """List (GET) or create (POST) inward other-material lots (app admin only)."""

    serializer_class = CreateInwardOtherMaterialSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = OTHER_LOT_QUERYSET_FILTERS
    sort_options = OTHER_LOT_SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_inward_other_materials_list",
        summary=(
            "List inward other-material lots (filter by party / material "
            "type / product, sortable)"
        ),
        parameters=list_query_parameters(
            queryset_filters=OTHER_LOT_QUERYSET_FILTERS,
            sort_options=OTHER_LOT_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: InwardOtherMaterialListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return InwardOtherMaterial.objects.select_related(
            "party",
            "recipe__product",
            "recipe__material_type",
            "created_by",
            "return_order__order",
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
        entry = create_other_lot(
            party=data["party"],
            recipe=data["recipe"],
            quantity=data["quantity"],
            actor=request.user,
        )
        return Response(inward_other_material_payload(entry), status=status.HTTP_201_CREATED)
