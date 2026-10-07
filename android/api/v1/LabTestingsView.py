"""Lab tests: ``GET``/``POST`` ``lab/lab-testings``.

Path: ``/android/api/v1/lab/lab-testings``. Lab-tester token only.

``GET`` lists the lab tests, newest first, with the same shapes and filters as
the admin list (``api.sales_admin.LabTestingsView``).

``POST`` is how a lab tester submits a lot's verdict: the grow-out inputs plus
``result`` (Pass / Fail), for a lot waiting in ``Lab Testing``. **Pass** moves the
lot to ``In Use`` and **Fail** to ``Rejected``, stamping today as its effective
date (see ``aggregator.LabTestingOperations``). A lot an admin sent back is
tested again by the same call: its one record is updated, not duplicated.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import locked_raw_lot
from aggregator.LabTestingOperations import lab_testing_payload, submit_lab_test
from aggregator.models import InwardRawMaterial, LabTesting
from android.api.paginated_views import AndroidLabTesterPaginatedDateRangeListView
from api.inward_serializers import (
    LAB_TESTING_QUERYSET_FILTERS,
    LAB_TESTING_SORT_OPTIONS,
    CreateLabTestingSerializer,
    LabTestingListPageSerializer,
    LabTestingPayloadSerializer,
)
from api.sales_admin.LabTestingsView import LAB_TESTING_RELATED
from common.views.paginated_date_range import list_query_parameters

# Loaded through ``locked_raw_lot``, so the payload built from it needs no further queries.
LOT_RELATED = (
    "product",
    "party",
    "status",
    "created_by",
    "return_order__order",
    "lab_testing__tested_by",
)


class LabTestingsView(AndroidLabTesterPaginatedDateRangeListView):
    """List (GET) or submit (POST) lab tests (lab tester only)."""

    serializer_class = CreateLabTestingSerializer
    enforce_date_range_filters = False
    default_sort = ("-tested_at", "-pk")
    queryset_filters = LAB_TESTING_QUERYSET_FILTERS
    sort_options = LAB_TESTING_SORT_OPTIONS

    @extend_schema(
        operation_id="android_api_v1_lab_testings_list",
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

    @extend_schema(
        operation_id="android_api_v1_lab_testings_create",
        summary="Submit a lot's lab test (Pass -> In Use, Fail -> Rejected)",
        request=CreateLabTestingSerializer,
        responses={201: LabTestingPayloadSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateLabTestingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lot_public_id = data.pop("inward_raw_material").public_id
        with transaction.atomic():
            lot = locked_raw_lot(
                InwardRawMaterial.objects.select_related(*LOT_RELATED), lot_public_id
            )
            test = submit_lab_test(lot, data, request.user)
        return Response(lab_testing_payload(test, lot), status=status.HTTP_201_CREATED)
