"""Lab tester's queue: ``GET`` ``lab/pending-lots``.

Path: ``/android/api/v1/lab/pending-lots``. Every raw-material lot currently in
``Lab Testing`` -- freshly booked, or sent back by an admin for a re-test -- is
here for the lab tester to test, oldest first. A lot sent back still carries
its earlier ``lab_testing`` (``result`` null), so the app can pre-fill the form.

Same shapes and filters as the godown/admin lot lists (``api.inward_serializers``).
Lab-tester token only; lots of frozen products are not listed.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.InwardOperations import inward_raw_material_payload
from aggregator.models import InwardRawMaterial, StatusIds
from android.api.paginated_views import AndroidLabTesterPaginatedDateRangeListView
from api.inward_serializers import (
    RAW_LOT_QUERYSET_FILTERS,
    RAW_LOT_SORT_OPTIONS,
    InwardRawMaterialListPageSerializer,
)
from common.views.paginated_date_range import list_query_parameters

# The status filter is meaningless here: the queue is the Lab Testing lots.
PENDING_LOT_FILTERS = tuple(f for f in RAW_LOT_QUERYSET_FILTERS if f.name != "status")


class LabPendingLotsView(AndroidLabTesterPaginatedDateRangeListView):
    """List the lots waiting for a lab test (lab tester only)."""

    enforce_date_range_filters = False
    default_sort = ("created_at", "pk")
    queryset_filters = PENDING_LOT_FILTERS
    sort_options = RAW_LOT_SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_lab_pending_lots_list",
        summary="List raw-material lots waiting for a lab test (oldest first)",
        parameters=list_query_parameters(
            queryset_filters=PENDING_LOT_FILTERS,
            sort_options=RAW_LOT_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: InwardRawMaterialListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return InwardRawMaterial.objects.filter(
            status_id=StatusIds.LAB_TESTING.value, product__is_usable=True
        ).select_related(
            "product", "party", "status", "created_by", "return_order__order", "lab_testing"
        )

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [inward_raw_material_payload(entry) for entry in page_items]
