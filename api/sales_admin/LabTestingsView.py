"""Lab testing list endpoint: ``GET`` ``/api/sales-admin/lab-testings``.

Only an application Admin may view the lab tests (``admin_required``); entering
and editing a test is the lab tester's job (see ``android.api.v1.LabTestingsView``).
Each row is one lot's grow-out test with its computed ``genetical_impurity`` /
``grow_out_test`` and the lot it belongs to. Tests of soft-deleted lots and of
frozen products are not listed.

Every test is exposed by its ``public_id`` (``LT-…``); the primary key is never
sent out.
"""

from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.LabTestingOperations import lab_testing_payload
from aggregator.models import LabTesting
from api.inward_serializers import (
    LAB_TESTING_QUERYSET_FILTERS,
    LAB_TESTING_SORT_OPTIONS,
    LabTestingListPageSerializer,
)
from api.paginated_views import AdminPaginatedDateRangeListView
from common.views.paginated_date_range import list_query_parameters

LAB_TESTING_RELATED = (
    "tested_by",
    "inward_raw_material__product",
    "inward_raw_material__party",
    "inward_raw_material__status",
    "inward_raw_material__created_by",
    "inward_raw_material__return_order__order",
)


class LabTestingsView(AdminPaginatedDateRangeListView):
    """List lab tests (app admin only)."""

    enforce_date_range_filters = False
    default_sort = ("-tested_at", "-pk")
    queryset_filters = LAB_TESTING_QUERYSET_FILTERS
    sort_options = LAB_TESTING_SORT_OPTIONS

    @extend_schema(
        operation_id="sales_admin_lab_testings_list",
        summary="List lab tests (filter by product / result / lot status, sortable)",
        parameters=list_query_parameters(
            queryset_filters=LAB_TESTING_QUERYSET_FILTERS,
            sort_options=LAB_TESTING_SORT_OPTIONS,
            date_window="none",
        ),
        responses={200: LabTestingListPageSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self, request: Request) -> QuerySet:
        return LabTesting.objects.filter(
            inward_raw_material__is_deleted=False,
            inward_raw_material__product__is_usable=True,
        ).select_related(*LAB_TESTING_RELATED)

    def serialize_page(self, page_items, request: Request) -> list[dict]:
        return [lab_testing_payload(test) for test in page_items]
