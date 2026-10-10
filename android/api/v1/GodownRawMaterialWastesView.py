"""Godown raw-material waste: GET/POST ``godown/raw-material-wastes``.

The Android counterpart of ``api.sales_admin.RawMaterialWastesView``: same
request/response shapes, filters and rules, for the godown manager. Recording
waste writes off ``quantity_kg`` of a product's raw material, refused (400) when
it exceeds the product's unpacked raw kilograms
(``InventoryOperations.record_raw_waste``).

Together with ``UpdateGodownRawMaterialWasteView`` (PATCH/DELETE one row) this is
everything a godown manager may do with waste: add, list, edit and delete a
waste *entry*. Waste orders are admin-only. Godown-manager token only.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.InwardOperations import raw_waste_payload
from aggregator.models import RawMaterialWaste
from android.api.paginated_views import AndroidGodownPaginatedDateRangeListView
from api.inward_serializers import (
    RAW_WASTE_QUERYSET_FILTERS,
    RAW_WASTE_SORT_OPTIONS,
    CreateRawMaterialWasteSerializer,
    RawMaterialWasteListPageSerializer,
    RawMaterialWastePayloadSerializer,
)
from common.views.paginated_date_range import list_query_parameters


class GodownRawMaterialWastesView(AndroidGodownPaginatedDateRangeListView):
    """List (GET) or record (POST) raw-material waste (godown manager only)."""

    serializer_class = CreateRawMaterialWasteSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = RAW_WASTE_QUERYSET_FILTERS
    sort_options = RAW_WASTE_SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_godown_raw_material_wastes_list",
        summary="List raw-material waste (filter by product, sortable)",
        parameters=list_query_parameters(
            queryset_filters=RAW_WASTE_QUERYSET_FILTERS,
            sort_options=RAW_WASTE_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: RawMaterialWasteListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return RawMaterialWaste.objects.filter(product__is_usable=True).select_related(
            "product", "created_by"
        )

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [raw_waste_payload(entry) for entry in page_items]

    @extend_schema(
        operation_id="android_api_v1_godown_raw_material_wastes_create",
        summary="Record raw-material waste",
        request=CreateRawMaterialWasteSerializer,
        responses={201: RawMaterialWastePayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateRawMaterialWasteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            entry = InventoryOperations.record_raw_waste(
                product=data["product"],
                quantity_kg=data["quantity_kg"],
                reason=data["reason"],
                actor=request.user,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"quantity_kg": str(exc)}) from None
        return Response(raw_waste_payload(entry), status=status.HTTP_201_CREATED)
