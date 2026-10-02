"""Godown inward raw-material lots: GET/POST ``godown/inward-raw-materials``.

The Android counterpart of ``api.sales_admin.InwardRawMaterialsView``: same
request/response shapes and filters (``api.inward_serializers``), same booking
rules (``InwardOperations``). A new lot starts ``Lab Testing``; ``lot_no`` is
required. Godown-manager token only.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import inward_raw_material_payload, today
from aggregator.models import InwardRawMaterial
from android.api.paginated_views import AndroidGodownPaginatedDateRangeListView
from api.inward_serializers import (
    RAW_LOT_QUERYSET_FILTERS,
    RAW_LOT_SORT_OPTIONS,
    CreateInwardRawMaterialSerializer,
    InwardRawMaterialListPageSerializer,
    InwardRawMaterialPayloadSerializer,
)
from common.views.paginated_date_range import list_query_parameters


class GodownInwardRawMaterialsView(AndroidGodownPaginatedDateRangeListView):
    """List (GET) or book (POST) inward raw-material lots (godown manager only)."""

    serializer_class = CreateInwardRawMaterialSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = RAW_LOT_QUERYSET_FILTERS
    sort_options = RAW_LOT_SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_godown_inward_raw_materials_list",
        summary="List inward raw-material lots (filter by product / party / status, sortable)",
        parameters=list_query_parameters(
            queryset_filters=RAW_LOT_QUERYSET_FILTERS,
            sort_options=RAW_LOT_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: InwardRawMaterialListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return InwardRawMaterial.objects.select_related("product", "party", "status", "created_by")

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [inward_raw_material_payload(entry) for entry in page_items]

    @extend_schema(
        operation_id="android_api_v1_godown_inward_raw_materials_create",
        summary="Book an inward raw-material lot",
        request=CreateInwardRawMaterialSerializer,
        responses={201: InwardRawMaterialPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateInwardRawMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry = InwardRawMaterial.objects.create(
            product=data["product"],
            party=data["party"],
            lot_no=data["lot_no"],
            quantity_kg=data["quantity_kg"],
            lab_sampling_date=data.get("lab_sampling_date") or today(),
            created_by=request.user,
        )
        return Response(inward_raw_material_payload(entry), status=status.HTTP_201_CREATED)
