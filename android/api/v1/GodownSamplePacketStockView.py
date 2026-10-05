"""Godown sample-packet (loose) stock position: ``GET`` ``godown/sample-packet-stock``.

The Android counterpart of ``api.sales_admin.SamplePacketStockView``: the same
on-hand/reserved/consumed/available figures for every counted loose
``(product, packet_weight)`` pool, reusing the same payload builder and
``InventoryOperations``. Godown-manager token only.

Independent of the sealed-bag snapshot and of ``godown/bag-stock``: the loose
count runs on its own, optional date lifecycle, so this may report an older
``snapshot_date`` than today even when the bag count is current.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from android.api.base import AndroidGodownBaseView
from api.sales_admin.SamplePacketStockView import (
    LooseStockPositionSerializer,
    loose_line_payload,
)


class GodownSamplePacketStockView(AndroidGodownBaseView):
    """Read the current loose-packet position for every counted pool (godown manager only)."""

    @extend_schema(
        operation_id="android_api_v1_godown_sample_packet_stock",
        summary="Read the sample-packet (loose) stock position",
        description=(
            "The live on-hand/reserved/consumed/available figures for every "
            "counted ``(product, packet_weight)`` pool -- the same position "
            "``godown/update-sample-packet-stock`` would report back, but "
            "readable before (or without) submitting a count. "
            "``snapshot_date`` is the date the loose count was last taken, null "
            "when none has ever been recorded."
        ),
        responses={200: LooseStockPositionSerializer},
    )
    def get(self, request: Request) -> Response:
        snapshot_date = InventoryOperations.latest_loose_snapshot_date()
        return Response(
            {
                "snapshot_date": snapshot_date.isoformat() if snapshot_date else None,
                "lines": [
                    loose_line_payload(entry)
                    for entry in InventoryOperations.loose_stock_position()
                    # A frozen product is not shown on the stock pages at all.
                    if entry["product"].is_usable
                ],
            }
        )
