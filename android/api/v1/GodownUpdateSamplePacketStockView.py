"""Godown loose-packet stock count:
``POST``/``PATCH`` ``godown/update-sample-packet-stock``.

The Android counterpart of ``api.sales_admin.UpdateSamplePacketStockView``: the
same list-of-lines ``{"counts": [{"product", "packet_weight", "packets"}, ...]}``
payload and serializers, the same ``(product, packet_weight)`` identity and
``packable_pairs`` universe, the same ``POST`` (every pair the business packs
gets a row for today, the unnamed ones zero-filled) / ``PATCH`` (only the lines
named) split, and the same refusals -- a pair the business does not pack, a pair
named twice, an unusable product, and raw material that cannot cover the packets
(``InventoryOperations``). Godown-manager token only.

The loose count is optional and runs on its own date lifecycle: the sealed-bag
snapshot (``godown/update-bag-stock``) is never touched here, and a missing loose
count never blocks order verification.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from android.api.base import AndroidGodownBaseView
from api.sales_admin.UpdateSamplePacketStockView import (
    LooseStockPayloadSerializer,
    UpdateLooseStockSerializer,
    packable_pairs,
)


class GodownUpdateSamplePacketStockView(AndroidGodownBaseView):
    """Record the loose-packet count from the godown floor (godown manager only)."""

    serializer_class = UpdateLooseStockSerializer

    def _resolve_counts(self, serializer) -> dict:
        """Map validated lines to ``{(product, packet_weight): packets}``.

        Mirrors ``UpdateLooseStockView._resolve_counts``: a pair the business does
        not pack, a pair of an unusable product, and a pair named twice in one
        payload (which would otherwise let the last line silently win) are all
        refused, exactly as on the web.
        """
        lines = serializer.validated_data["counts"]
        valid = packable_pairs()
        everything = packable_pairs(usable_only=False)

        counts = {}
        unknown, duplicates = [], []
        frozen: list[str] = []
        for line in lines:
            key = (line["product"], line["packet_weight"])
            if key not in valid and key in everything:
                frozen.append(key[0])
                continue
            if key not in valid:
                unknown.append(f"{key[0]} @ {key[1]}kg")
                continue
            resolved = valid[key]
            if resolved in counts:
                duplicates.append(f"{key[0]} @ {key[1]}kg")
                continue
            counts[resolved] = line["packets"]

        errors = []
        if frozen:
            errors.append(
                "Stock cannot be counted for unusable product(s): "
                + ", ".join(sorted(set(frozen)))
                + "."
            )
        if unknown:
            errors.append("No packaging exists for: " + ", ".join(sorted(unknown)) + ".")
        if duplicates:
            errors.append(
                "Repeated product/packet-weight pairs: " + ", ".join(sorted(duplicates)) + "."
            )
        if errors:
            raise serializers.ValidationError({"counts": " ".join(errors)})
        return counts

    def _respond(self, snapshots):
        return Response(
            [InventoryOperations.loose_stock_payload(s) for s in snapshots],
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="android_api_v1_godown_update_sample_packet_stock",
        summary="Replace the whole loose-packet stock count",
        description=(
            "Every (product, packet_weight) pair the business packs receives a "
            "loose row for today. Pairs absent from ``counts`` are recorded as "
            "zero packets. Does not touch the sealed-bag snapshot."
        ),
        request=UpdateLooseStockSerializer,
        responses={200: LooseStockPayloadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Whole-day loose count",
                value={
                    "counts": [
                        {
                            "product": "P-A1B2C3D4E0F1",
                            "packet_weight": "1.000",
                            "packets": 12,
                        },
                        {
                            "product": "P-A1B2C3D4E0F1",
                            "packet_weight": "0.500",
                            "packets": 0,
                        },
                    ]
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request: Request) -> Response:
        serializer = UpdateLooseStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provided = self._resolve_counts(serializer)

        full_counts = {pair: provided.get(pair, 0) for pair in packable_pairs().values()}
        try:
            # Pairs of an unusable product cannot be counted; their last figure is
            # carried forward so freezing a product never moves its stock.
            snapshots = InventoryOperations.record_loose_stocks(
                counts=full_counts, actor=request.user, carry_frozen=True
            )
        except ValueError as exc:
            raise serializers.ValidationError({"counts": str(exc)}) from None
        return self._respond(snapshots)

    @extend_schema(
        operation_id="android_api_v1_godown_update_sample_packet_stock_partial",
        summary="Partially update the loose-packet stock count",
        description=(
            "Only the pairs named in ``counts`` are written; every other loose "
            "row is left as it is."
        ),
        request=UpdateLooseStockSerializer,
        responses={200: LooseStockPayloadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Partial loose count",
                value={
                    "counts": [
                        {
                            "product": "P-A1B2C3D4E0F1",
                            "packet_weight": "1.000",
                            "packets": 12,
                        }
                    ]
                },
                request_only=True,
            ),
        ],
    )
    def patch(self, request: Request) -> Response:
        serializer = UpdateLooseStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        counts = self._resolve_counts(serializer)
        try:
            snapshots = InventoryOperations.record_loose_stocks(
                counts=counts, actor=request.user, carry_forward=True
            )
        except ValueError as exc:
            raise serializers.ValidationError({"counts": str(exc)}) from None
        return self._respond(snapshots)
