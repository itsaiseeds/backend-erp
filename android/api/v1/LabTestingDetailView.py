"""One lab test: ``GET``/``PATCH`` ``lab/lab-testing/<public_id>``.

Path: ``/android/api/v1/lab/lab-testing/<LT-…>``. Lab-tester token only;
tests of soft-deleted lots are a 404.

``GET`` is the full record: every input, the computed ``genetical_impurity`` /
``grow_out_test``, the verdict and who gave it, and the lot it decides.

``PATCH`` corrects a test. Any input (plants, female / OT counts,
comment) may always be edited. Changing ``result`` also moves the lot between
``In Use`` and ``Rejected``: ``Pass -> Fail`` is refused (400) when the lot's
kilograms are already packed into bags or sample packets -- no stock figure may
go negative -- while ``Fail -> Pass`` is always allowed. On a lot an admin sent
back to ``Lab Testing`` the first ``result`` sent is the re-test itself. See
``aggregator.LabTestingOperations``.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.LabTestingOperations import (
    lab_testing_payload,
    locked_lot_for_test,
    update_lab_test,
)
from aggregator.models import InwardRawMaterial, LabTesting
from android.api.base import AndroidLabTesterBaseView
from api.inward_serializers import LabTestingPayloadSerializer, UpdateLabTestingSerializer
from api.sales_admin.LabTestingsView import LAB_TESTING_RELATED

from .LabTestingsView import LOT_RELATED


class LabTestingDetailView(AndroidLabTesterBaseView):
    """Read or correct one lab test (lab tester only)."""

    serializer_class = UpdateLabTestingSerializer

    @extend_schema(
        operation_id="android_api_v1_lab_testing_retrieve",
        summary="Get one lab test in detail",
        responses={200: LabTestingPayloadSerializer},
    )
    def get(self, request: Request, public_id: str) -> Response:
        test = get_object_or_404(
            LabTesting.objects.filter(inward_raw_material__is_deleted=False).select_related(
                *LAB_TESTING_RELATED
            ),
            public_id=public_id,
        )
        return Response(lab_testing_payload(test))

    @extend_schema(
        operation_id="android_api_v1_lab_testing_update",
        summary="Edit a lab test (a changed result moves the lot In Use <-> Rejected)",
        request=UpdateLabTestingSerializer,
        responses={200: LabTestingPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        with transaction.atomic():
            lot = locked_lot_for_test(
                InwardRawMaterial.objects.select_related(*LOT_RELATED), public_id
            )
            serializer = UpdateLabTestingSerializer(instance=lot.lab_testing, data=request.data)
            serializer.is_valid(raise_exception=True)
            test = update_lab_test(lot, serializer.validated_data, request.user)
        return Response(lab_testing_payload(test, lot))
