"""Lab testing detail endpoint: ``GET`` ``/api/sales-admin/lab-testing/<public_id>``.

Path: ``/api/sales-admin/lab-testing/<LT-…>``. Read-only for an application
Admin: the full record of one lot's grow-out test -- every input, the computed
``genetical_impurity`` / ``grow_out_test``, the verdict and who gave it, and the
lot it decides. Soft-deleted lots' tests are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from aggregator.LabTestingOperations import lab_testing_payload
from aggregator.models import LabTesting
from api.admin import AdminApiView
from api.inward_serializers import LabTestingPayloadSerializer

from .LabTestingsView import LAB_TESTING_RELATED


class LabTestingDetailView(AdminApiView):
    """Read one lab test (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Get one lab test in detail",
        responses={200: LabTestingPayloadSerializer},
    )
    def get(self, request, public_id: str):
        test = get_object_or_404(
            LabTesting.objects.filter(inward_raw_material__is_deleted=False).select_related(
                *LAB_TESTING_RELATED
            ),
            public_id=public_id,
        )
        return Response(lab_testing_payload(test))
