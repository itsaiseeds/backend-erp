"""Inward-movement export: ``GET /api/sales-admin/export/inward-entries``.

Every live inward entry -- raw material (``IR-…``) and other material
(``IO-…``) -- **booked** (``created_at``) inside the window, grouped by the IST
day it was booked on::

    [{"date": "2026-09-01", "raw_materials": [...], "other_materials": [...]}, ...]

Days are ascending and only days with at least one entry appear. Rows are the
same payloads the inward list endpoints return, plus ``created_at``. The window
contract is in :mod:`api.export_views`.
"""

from __future__ import annotations

from datetime import date, datetime

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.InwardOperations import (
    inward_other_material_payload,
    inward_raw_material_payload,
)
from aggregator.models import InwardOtherMaterial, InwardRawMaterial
from api.export_serializers import ExportInwardDaySerializer
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    export_response_serializer,
)

ExportInwardEntriesResponseSerializer = export_response_serializer(
    "ExportInwardEntriesResponseSerializer", ExportInwardDaySerializer
)


class ExportInwardEntriesView(AdminDateRangeExportView):
    """Export the inward entries booked in a date window, grouped by day."""

    def export(self, window: DateWindow) -> list[dict]:
        days: dict[date, dict[str, list[dict]]] = {}

        def bucket(created_at: datetime) -> dict[str, list[dict]]:
            day = timezone.localtime(created_at).date()
            return days.setdefault(day, {"raw_materials": [], "other_materials": []})

        raw_entries = (
            window.created_between(InwardRawMaterial.objects.all())
            .select_related("product", "party")
            .order_by("created_at", "id")
        )
        for raw in raw_entries:
            bucket(raw.created_at)["raw_materials"].append(
                {**inward_raw_material_payload(raw), "created_at": raw.created_at.isoformat()}
            )

        other_entries = (
            window.created_between(InwardOtherMaterial.objects.all())
            .select_related("recipe__product", "party")
            .order_by("created_at", "id")
        )
        for other in other_entries:
            bucket(other.created_at)["other_materials"].append(
                {
                    **inward_other_material_payload(other),
                    "created_at": other.created_at.isoformat(),
                }
            )

        return [{"date": day.isoformat(), **days[day]} for day in sorted(days)]

    @extend_schema(
        operation_id="sales_admin_export_inward_entries",
        summary="Export inward entries booked in a date range, grouped by day",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportInwardEntriesResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
