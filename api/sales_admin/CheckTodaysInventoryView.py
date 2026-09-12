"""Inventory-readiness endpoint: ``GET`` ``/api/sales-admin/check-todays-inventory``.

Only an application Admin may call this (``admin_required`` on ``AdminApiView``,
the session-only web base). It reports whether today's physical stock count is
complete -- i.e. every active packaging has an ``InventorySnapshot`` row for
today -- and which admins are authorised to upload that count
(``Admin.can_update_stock_count``).

``is_complete`` covers **sealed bags only**. The loose count is optional by
design, so a missing or stale one never blocks order verification;
``loose_snapshot_date`` reports when it was last taken (``null`` if never) so
the frontend can surface how stale it is.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator import InventoryOperations
from api.admin import AdminApiView
from authentication.models import Admin


class MissingPackagingSerializer(serializers.Serializer):
    """Output shape for one packaging that has not been counted today."""

    public_id = serializers.CharField()
    product = serializers.DictField(child=serializers.CharField())


class StockAdminSerializer(serializers.Serializer):
    """Output shape for one admin authorised to record the daily count."""

    name = serializers.CharField()
    phone_number = serializers.CharField()


class CheckTodaysInventoryPayloadSerializer(serializers.Serializer):
    """Output shape for the readiness report."""

    is_complete = serializers.BooleanField()
    snapshot_date = serializers.DateField()
    loose_snapshot_date = serializers.DateField(allow_null=True)
    missing_packagings = MissingPackagingSerializer(many=True)
    stock_admins = StockAdminSerializer(many=True)


def missing_packaging_payload(packaging) -> dict:
    """Response shape for one uncounted packaging (never exposes the primary key)."""
    return {
        "public_id": packaging.public_id,
        "product": {
            "public_id": packaging.product.public_id,
            "name": packaging.product.name,
        },
    }


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
            "optional and never blocks verification. ``loose_snapshot_date`` "
            "is when loose stock was last counted, or null if never."
        ),
        responses={200: CheckTodaysInventoryPayloadSerializer},
    )
    def get(self, request):
        missing = InventoryOperations.missing_packagings().select_related("product")
        stock_admins = Admin.objects.filter(
            can_update_stock_count=True
        ).select_related("user")
        loose_date = InventoryOperations.latest_loose_snapshot_date()
        return Response(
            {
                "is_complete": InventoryOperations.is_stock_count_complete(),
                "snapshot_date": InventoryOperations.today().isoformat(),
                "loose_snapshot_date": loose_date.isoformat() if loose_date else None,
                "missing_packagings": [missing_packaging_payload(p) for p in missing],
                "stock_admins": [stock_admin_payload(a) for a in stock_admins],
            }
        )
