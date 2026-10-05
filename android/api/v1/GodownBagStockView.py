"""Godown bag-stock position: ``GET`` ``godown/bag-stock``.

The Android counterpart of ``api.sales_admin.BagStockView``: the same
on-hand/reserved/consumed/available figures for every counted sealed-bag
packaging, reusing the same payload builder and ``InventoryOperations``.
Godown-manager token only.

The app shows this alongside the count the manager is entering so a lot that
has already been counted today reads back its live position without a second
screen -- the same table a web admin sees, just read through a bearer token
instead of a session.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from android.api.base import AndroidGodownBaseView
from api.sales_admin.BagStockView import BagStockPositionSerializer, bag_line_payload


class GodownBagStockView(AndroidGodownBaseView):
    """Read the current bag-stock position for every counted packaging (godown manager only)."""

    @extend_schema(
        operation_id="android_api_v1_godown_bag_stock",
        summary="Read the bag-stock position",
        description=(
            "The live on-hand/reserved/consumed/available figures for every "
            "counted sealed-bag packaging -- the same position "
            "``godown/update-bag-stock`` would report back, but readable before "
            "(or without) submitting a count. ``snapshot_date`` is the date the "
            "bag count was last taken, null when none has ever been recorded."
        ),
        responses={200: BagStockPositionSerializer},
    )
    def get(self, request: Request) -> Response:
        snapshot_date = InventoryOperations.latest_snapshot_date()
        return Response(
            {
                "snapshot_date": snapshot_date.isoformat() if snapshot_date else None,
                "lines": [
                    bag_line_payload(entry)
                    for entry in InventoryOperations.stock_position(snapshot_date)
                    # A frozen product is not shown on the stock pages at all.
                    if entry["product"].is_usable
                ],
            }
        )
