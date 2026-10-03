"""Recent dispatch lot numbers: ``GET /api/sales-admin/dispatch-lot-numbers/``.

An LRU list for the lot-number box on the dispatch form: the lot numbers most
recently *used on a dispatch*, newest first, so the admin can pick one instead of
retyping it.

It is derived, not stored. ``DispatchEntryItem.lot_number`` is the only source,
so there is no second table to keep in step with it, nothing to invalidate, and
**inward lot numbers can never appear** -- they live on the inward models and are
not read here. A lot's recency is the latest ``created_at`` of any live line that
carries it, so re-using a lot moves it back to the top and a lot nobody has
dispatched in a while drops off the end of the ``limit``.

* ``?limit=<n>`` -- how many to return; default 10, at most 50.
* ``?q=<text>`` -- keep only lot numbers starting with this text
  (case-insensitive), for type-ahead.
"""

from __future__ import annotations

from django.db.models import Max
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import DispatchEntryItem
from api.admin import AdminApiView

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class DispatchLotNumberSerializer(serializers.Serializer):
    """Output shape for one recently used lot number (schema only)."""

    lot_number = serializers.CharField()
    last_used_at = serializers.DateTimeField()


class DispatchLotNumbersSerializer(serializers.Serializer):
    """Output shape for the response envelope (schema only)."""

    results = DispatchLotNumberSerializer(many=True)


def recent_dispatch_lot_numbers(limit: int, prefix: str = "") -> list[dict]:
    """The ``limit`` most recently dispatched lot numbers, newest first.

    ``DispatchEntryItem``'s default manager already hides soft-deleted lines.
    The ``lot_number`` tiebreak keeps the order stable when two lots share a
    timestamp.
    """
    rows = DispatchEntryItem.objects.exclude(lot_number="")
    if prefix:
        rows = rows.filter(lot_number__istartswith=prefix)
    rows = (
        rows.values("lot_number")
        .annotate(last_used_at=Max("created_at"))
        .order_by("-last_used_at", "lot_number")[:limit]
    )
    return list(rows)


def _parse_limit(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_LIMIT
    try:
        limit = int(raw)
    except ValueError:
        raise serializers.ValidationError({"limit": "Must be an integer."}) from None
    if not 1 <= limit <= MAX_LIMIT:
        raise serializers.ValidationError(
            {"limit": f"Must be between 1 and {MAX_LIMIT}."}
        )
    return limit


class GetDispatchLotNumbersView(AdminApiView):
    """Recently used dispatch lot numbers, most recent first."""

    admin_required = True

    @extend_schema(
        operation_id="sales_admin_get_dispatch_lot_numbers",
        summary="Recently used dispatch lot numbers (LRU, dispatch lots only)",
        parameters=[
            OpenApiParameter(
                "limit",
                int,
                description=f"Entries to return (default {DEFAULT_LIMIT}, max {MAX_LIMIT}).",
            ),
            OpenApiParameter(
                "q", str, description="Only lot numbers starting with this text."
            ),
        ],
        responses={200: DispatchLotNumbersSerializer},
    )
    def get(self, request: Request) -> Response:
        limit = _parse_limit(request.query_params.get("limit"))
        prefix = request.query_params.get("q", "").strip()
        return Response({"results": recent_dispatch_lot_numbers(limit, prefix)})
