"""Godown inventory-readiness report: ``GET`` ``godown/check-todays-inventory``.

The Android counterpart of ``api.sales_admin.CheckTodaysInventoryView``: the same
readiness report (``is_complete`` for today's sealed-bag count, plus the name and
phone number of every admin holding ``Admin.can_update_stock_count``), reusing
the same payload builders and ``InventoryOperations``. Godown-manager token only.

``is_complete`` is the same compulsory gate order verification reads, so a
godown manager can see whether the floor is counted before asking an admin to
count it. A godown manager counts without an ``Admin`` profile, so they never
appear in ``stock_admins`` themselves.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from android.api.base import AndroidGodownBaseView
from api.sales_admin.CheckTodaysInventoryView import (
    CheckTodaysInventoryPayloadSerializer,
    stock_admin_payload,
)
from authentication.models import Admin


class GodownCheckTodaysInventoryView(AndroidGodownBaseView):
    """Report whether today's stock count is complete (godown manager only)."""

    @extend_schema(
        operation_id="android_api_v1_godown_check_todays_inventory",
        summary="Check whether today's stock count is complete",
        description=(
            "``is_complete`` covers sealed bags only -- the loose count is "
            "optional and never blocks order verification. ``stock_admins`` lists "
            "the admins who may upload the count; a godown manager counts from the "
            "app without an admin profile and is therefore not listed."
        ),
        responses={200: CheckTodaysInventoryPayloadSerializer},
    )
    def get(self, request: Request) -> Response:
        stock_admins = Admin.objects.filter(can_update_stock_count=True).select_related("user")
        return Response(
            {
                "is_complete": InventoryOperations.is_stock_count_complete(),
                "stock_admins": [stock_admin_payload(admin) for admin in stock_admins],
            }
        )
