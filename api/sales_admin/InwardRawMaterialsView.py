"""Inward raw material endpoint: ``GET``/``POST`` ``/api/sales-admin/inward-raw-materials``.

Only an application Admin may view or create lots (``admin_required``). A lot
records raw-material replenishment: how many kilograms of a ``Product`` came in
from a ``Party``, when it was sampled for the lab, and its ``status``. The
entry's date is its ``created_at``, and ``lab_sampling_date`` defaults to that
same day (a lot arrives for lab testing the day it's booked) unless given
explicitly. ``effective_date`` is **not** accepted here -- flipping ``status``
to ``In Use`` with ``PATCH`` stamps it with today (see
``UpdateInwardRawMaterialView``), so a freshly booked lot never counts toward
stock by accident.

Every lot is exposed by its ``public_id`` (``IR-…``); the primary key is never
sent out.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import create_raw_lot, inward_raw_material_payload, today
from aggregator.models import InwardRawMaterial
from api.inward_serializers import (
    RAW_LOT_QUERYSET_FILTERS,
    RAW_LOT_SORT_OPTIONS,
    CreateInwardRawMaterialSerializer,
    InwardRawMaterialListPageSerializer,
    InwardRawMaterialPayloadSerializer,
)
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import (
    list_query_parameters,
)


class InwardRawMaterialsView(AdminPaginatedDateRangeListView):
    """List (GET) or create (POST) inward raw-material lots (app admin only)."""

    serializer_class = CreateInwardRawMaterialSerializer
    enforce_date_range_filters = False
    default_sort = ("-created_at", "pk")
    queryset_filters = RAW_LOT_QUERYSET_FILTERS
    sort_options = RAW_LOT_SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_inward_raw_materials_list",
        summary=(
            "List inward raw-material lots (filter by product / party / status / "
            "effective date range, sortable)"
        ),
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
        summary="Create an inward raw-material lot",
        request=CreateInwardRawMaterialSerializer,
        responses={201: InwardRawMaterialPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateInwardRawMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry = create_raw_lot(
            product=data["product"],
            party=data["party"],
            lot_no=data["lot_no"],
            quantity_kg=data["quantity_kg"],
            lab_sampling_date=data.get("lab_sampling_date") or today(),
            actor=request.user,
        )
        return Response(inward_raw_material_payload(entry), status=status.HTTP_201_CREATED)
