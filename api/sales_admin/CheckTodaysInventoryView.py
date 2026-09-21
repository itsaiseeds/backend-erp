"""Inventory-readiness endpoint: ``GET`` ``/api/sales-admin/check-todays-inventory``.

Only an application Admin may call this (``admin_required`` on ``AdminApiView``,
the session-only web base). It reports whether today's physical stock count is
complete -- i.e. every active packaging has an ``InventorySnapshot`` row for
today -- and which admins are authorised to upload that count
(``Admin.can_update_stock_count``).

``is_complete`` covers **sealed bags only**. The loose count is optional by
design, so a missing or stale one never blocks order verification.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator import InventoryOperations
from api.admin import AdminApiView
from authentication.models import Admin


class StockAdminSerializer(serializers.Serializer):
    """Output shape for one admin authorised to record the daily count."""

    name = serializers.CharField()
    phone_number = serializers.CharField()


class CheckTodaysInventoryPayloadSerializer(serializers.Serializer):
    """Output shape for the readiness report."""

    is_complete = serializers.BooleanField()
    stock_admins = StockAdminSerializer(many=True)


def stock_admin_payload(admin) -> dict:
    """Response shape for one stock-update admin."""
    return {
        "name": admin.user.name,
        "phone_number": admin.user.phone_number,
    }


class CheckTodaysInventoryView(AdminApiView):
    """Report whether today's stock count is complete (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Check whether today's stock count is complete",
        description=(
            "``is_complete`` covers sealed bags only -- the loose count is "
            "optional and never blocks order verification."
        ),
        responses={200: CheckTodaysInventoryPayloadSerializer},
    )
    def get(self, request):
        stock_admins = Admin.objects.filter(
            can_update_stock_count=True
        ).select_related("user")
        return Response(
            {
                "is_complete": InventoryOperations.is_stock_count_complete(),
                "stock_admins": [stock_admin_payload(a) for a in stock_admins],
            }
        )
