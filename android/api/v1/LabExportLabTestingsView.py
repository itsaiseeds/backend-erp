"""Lab-testing export: ``GET`` ``lab/export/lab-testings``.

Path: ``/android/api/v1/lab/export/lab-testings``. Lab-tester token only.

The Android counterpart of ``api.sales_admin.ExportLabTestingsView``: the lab
tests tested inside an inclusive ``start_date`` .. ``end_date`` window (IST),
newest first, as the same lab-testing payloads the list returns. Both dates are
required and the window is capped, exactly as for the admin export (see
:mod:`api.export_views`).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from android.api.base import AndroidLabTesterBaseView
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    DateRangeExportMixin,
    DateWindow,
)
from api.sales_admin.ExportLabTestingsView import (
    ExportLabTestingsResponseSerializer,
    export_lab_testings,
)


class LabExportLabTestingsView(DateRangeExportMixin, AndroidLabTesterBaseView):
    """Export the lab tests done in a date window, newest first."""

    def export(self, window: DateWindow) -> list[dict]:
        return export_lab_testings(window)

    @extend_schema(
        operation_id="android_api_v1_lab_export_lab_testings",
        summary="Export lab tests done in a date range, newest first",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportLabTestingsResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
