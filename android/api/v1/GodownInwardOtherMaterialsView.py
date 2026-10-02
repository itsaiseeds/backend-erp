"""Godown inward other-material lots: GET/POST ``godown/inward-other-materials``.

The Android counterpart of ``api.sales_admin.InwardOtherMaterialsView``: same
shapes and filters (``api.inward_serializers``); booking stamps
``effective_date`` with today. Godown-manager token only.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import inward_other_material_payload, today
from aggregator.models import InwardOtherMaterial
from android.api.paginated_views import AndroidGodownPaginatedDateRangeListView
from api.inward_serializers import (
    OTHER_LOT_QUERYSET_FILTERS,
    OTHER_LOT_SORT_OPTIONS,
    CreateInwardOtherMaterialSerializer,
    InwardOtherMaterialListPageSerializer,
    InwardOtherMaterialPayloadSerializer,
)
from common.views.paginated_date_range import list_query_parameters


class GodownInwardOtherMaterialsView(AndroidGodownPaginatedDateRangeListView):
    """List (GET) or book (POST) inward other-material lots (godown manager only)."""

    serializer_class = CreateInwardOtherMaterialSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = OTHER_LOT_QUERYSET_FILTERS
    sort_options = OTHER_LOT_SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_godown_inward_other_materials_list",
        summary=(
            "List inward other-material lots (filter by party / material type / product / "
            "effective date range, sortable)"
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
            "party", "recipe__product", "recipe__material_type", "created_by"
        )

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [inward_other_material_payload(entry) for entry in page_items]

    @extend_schema(
        operation_id="android_api_v1_godown_inward_other_materials_create",
        summary="Book an inward other-material lot",
        request=CreateInwardOtherMaterialSerializer,
        responses={201: InwardOtherMaterialPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
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
