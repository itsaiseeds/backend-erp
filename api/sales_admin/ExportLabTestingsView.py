"""Lab-testing export: ``GET /api/sales-admin/export/lab-testings``.

Every live lab test **tested** (``tested_at``) inside the window, newest first,
as one flat list of the same payloads the lab-testing list returns: the
grow-out figures, the verdict, who tested and the lot the test belongs to. The
window contract is in :mod:`api.export_views`.

A test whose lot was sent back to the lab has no ``tested_at`` until it is
tested again, so it falls outside every window until then. Tests of
soft-deleted lots are left out; tests of frozen products are kept, because an
export reports history rather than offering a pick-list.

The Android counterpart is ``android.api.v1.LabExportLabTestingsView``.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.LabTestingOperations import lab_testing_payload
from aggregator.models import LabTesting
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    export_response_serializer,
)
from api.inward_serializers import LabTestingPayloadSerializer
from api.sales_admin.LabTestingsView import LAB_TESTING_RELATED

ExportLabTestingsResponseSerializer = export_response_serializer(
    "ExportLabTestingsResponseSerializer", LabTestingPayloadSerializer
)


def export_lab_testings(window: DateWindow) -> list[dict]:
    """The lab tests tested in ``window``, newest first (shared with the Android export)."""
    tests = (
        window.created_between(
            LabTesting.objects.filter(inward_raw_material__is_deleted=False),
            field="tested_at",
        )
        .select_related(*LAB_TESTING_RELATED)
        .order_by("-tested_at", "-id")
    )
    return [lab_testing_payload(test) for test in tests]


class ExportLabTestingsView(AdminDateRangeExportView):
    """Export the lab tests done in a date window, newest first."""

    def export(self, window: DateWindow) -> list[dict]:
        return export_lab_testings(window)

    @extend_schema(
        operation_id="sales_admin_export_lab_testings",
        summary="Export lab tests done in a date range, newest first",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportLabTestingsResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
