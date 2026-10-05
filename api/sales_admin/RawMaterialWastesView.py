"""Raw material waste endpoint: ``GET``/``POST`` ``/api/sales-admin/raw-material-wastes``.

Only an application Admin may view or record waste (``admin_required``). A row
writes off ``quantity_kg`` of a ``Product``'s raw material -- spoiled, spilled
or otherwise unusable -- with an optional free-text ``reason``. There is no
date: a waste row is a standing deduction from the product's unpacked raw pool
(see ``InventoryOperations.raw_wasted_kg``) from the moment it exists, and
shows up as ``wasted_kg`` on ``raw-material-stock`` (and on the godown manager's
stock view, which can see the figure but never write it).

A waste larger than the product's unpacked raw kilograms is refused (400).
Every row is exposed by its ``public_id`` (``WS-…``); the primary key is never
sent out. A wrong row is corrected with ``PATCH`` or removed with ``DELETE`` (see
``UpdateRawMaterialWasteView``).
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
from api.inward_serializers import (
    RAW_WASTE_QUERYSET_FILTERS,
    RAW_WASTE_SORT_OPTIONS,
    CreateRawMaterialWasteSerializer,
    RawMaterialWasteListPageSerializer,
    RawMaterialWastePayloadSerializer,
)
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import list_query_parameters


class RawMaterialWastesView(AdminPaginatedDateRangeListView):
    """List (GET) or record (POST) raw-material waste (app admin only)."""

    serializer_class = CreateRawMaterialWasteSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = RAW_WASTE_QUERYSET_FILTERS
    sort_options = RAW_WASTE_SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_raw_material_wastes_list",
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
        summary="Record raw-material waste",
        request=CreateRawMaterialWasteSerializer,
        responses={201: RawMaterialWastePayloadSerializer},
    )
    def post(self, request):
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
