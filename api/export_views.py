"""Sales-admin website base for a date-range export ``GET`` view.

An export is the whole period in one response, not a page: the caller names an
inclusive ``start_date`` .. ``end_date`` window (IST calendar dates) and gets
every matching record back as nested JSON::

    GET /api/sales-admin/export/orders?start_date=2026-09-01&end_date=2026-09-30

    {"start_date": "2026-09-01", "end_date": "2026-09-30", "count": 42,
     "results": [...]}

The window is capped at :data:`MAX_EXPORT_RANGE_DAYS` days, because the response
is unpaginated. A subclass implements only :meth:`AdminDateRangeExportView.export`.
It filters with the :class:`DateWindow` it is handed, and returns business
fields only: public ids, names, amounts and dates. Audit columns
(``created_by``, ``is_deleted``, ...) never go out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.db.models import QuerySet
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from .admin import AdminApiView

MAX_EXPORT_RANGE_DAYS = 31

EXPORT_QUERY_PARAMETERS = [
    OpenApiParameter(
        "start_date",
        OpenApiTypes.DATE,
        required=True,
        description="First day of the window (inclusive, IST).",
    ),
    OpenApiParameter(
        "end_date",
        OpenApiTypes.DATE,
        required=True,
        description=(
            "Last day of the window (inclusive, IST). At most "
            f"{MAX_EXPORT_RANGE_DAYS} days after-and-including start_date."
        ),
    ),
]


class ExportDateRangeQuerySerializer(serializers.Serializer):
    """Validates the ``start_date`` / ``end_date`` pair of an export."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        start, end = attrs["start_date"], attrs["end_date"]
        if start > end:
            raise serializers.ValidationError(
                "start_date must be less than or equal to end_date."
            )
        if (end - start).days + 1 > MAX_EXPORT_RANGE_DAYS:
            raise serializers.ValidationError(
                f"The date range may span at most {MAX_EXPORT_RANGE_DAYS} days."
            )
        return attrs


class ExportResponseSerializer(serializers.Serializer):
    """Output envelope shared by every export (schema only)."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    count = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


@dataclass(frozen=True)
class DateWindow:
    """An inclusive range of IST calendar days."""

    start_date: date
    end_date: date

    @property
    def start_datetime(self) -> datetime:
        """Midnight IST at the start of ``start_date`` (inclusive bound)."""
        return timezone.make_aware(datetime.combine(self.start_date, time.min))

    @property
    def end_datetime(self) -> datetime:
        """Midnight IST after ``end_date`` (exclusive bound)."""
        return timezone.make_aware(
            datetime.combine(self.end_date + timedelta(days=1), time.min)
        )

    def created_between(self, queryset: QuerySet, field: str = "created_at") -> QuerySet:
        """Narrow ``queryset`` to rows whose timestamp ``field`` falls in the window.

        A half-open ``[start, end + 1 day)`` datetime range rather than a
        ``__date`` lookup, so an index on the column can be used.
        """
        return queryset.filter(
            **{f"{field}__gte": self.start_datetime, f"{field}__lt": self.end_datetime}
        )


class AdminDateRangeExportView(AdminApiView):
    """Admin website ``GET`` export over a validated date window.

    A subclass implements :meth:`export` and wraps :meth:`get` in its own
    ``extend_schema`` (with :data:`EXPORT_QUERY_PARAMETERS`), the same way the
    paginated list views do.
    """

    admin_required = True

    def export(self, window: DateWindow) -> list[dict]:
        raise NotImplementedError(f"{type(self).__name__} must implement export(self, window).")

    def get(self, request: Request, *args, **kwargs):
        params = ExportDateRangeQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        window = DateWindow(
            start_date=params.validated_data["start_date"],
            end_date=params.validated_data["end_date"],
        )
        results = self.export(window)
        return Response(
            {
                "start_date": window.start_date.isoformat(),
                "end_date": window.end_date.isoformat(),
                "count": len(results),
                "results": results,
            }
        )
