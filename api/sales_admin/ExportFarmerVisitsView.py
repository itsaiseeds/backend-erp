"""Farmer-visit export: ``GET /api/sales-admin/export/farmer-visits``.

Every live farmer visit recorded (``created_at``) inside the window, oldest
first, across all field trips: the farmer's name, contact, village and land, the
crops they grow, the products of ours they use, the trip it was recorded on and
the sales person who met them. See :mod:`api.export_views` for the window
contract.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request

from aggregator.FieldTripOperations import farmer_visit_export_payload, farmer_visit_queryset
from api.export_serializers import ExportFarmerVisitSerializer
from api.export_views import (
    EXPORT_QUERY_PARAMETERS,
    AdminDateRangeExportView,
    DateWindow,
    export_response_serializer,
)

ExportFarmerVisitsResponseSerializer = export_response_serializer(
    "ExportFarmerVisitsResponseSerializer", ExportFarmerVisitSerializer
)


class ExportFarmerVisitsView(AdminDateRangeExportView):
    """Export the farmers recorded in a date window, across all field trips."""

    def export(self, window: DateWindow) -> list[dict]:
        visits = (
            window.created_between(farmer_visit_queryset())
            .select_related("field_trip__city", "field_trip__created_by")
            .order_by("created_at", "id")
        )
        return [farmer_visit_export_payload(visit) for visit in visits]

    @extend_schema(
        operation_id="sales_admin_export_farmer_visits",
        summary="Export farmers recorded on field trips in a date range",
        parameters=EXPORT_QUERY_PARAMETERS,
        responses={200: ExportFarmerVisitsResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
