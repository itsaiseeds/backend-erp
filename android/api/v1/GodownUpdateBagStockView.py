"""Godown sealed-bag stock count: ``POST``/``PATCH`` ``godown/update-bag-stock``.

The Android counterpart of ``api.sales_admin.UpdateBagStockView``: the same
``{"counts": {"<packaging public_id>": bags}}`` payload and serializers, the same
``POST`` (every active packaging of a usable product gets a row for today, the
unnamed ones zero-filled) / ``PATCH`` (only the packagings named) split, and the
same refusals -- unknown packaging, unusable product, and raw material that
cannot cover the bags (``InventoryOperations``). Loose packets have their own
endpoint, ``godown/update-sample-packet-stock``. Godown-manager token only.

A godown manager counts the floor, so the role itself grants
``User.can_update_stock_count``; no ``Admin`` profile is needed.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.models import ProductPackaging
from aggregator.ProductOperations import usable_packagings
from android.api.base import AndroidGodownBaseView
from api.sales_admin.UpdateBagStockView import (
    SnapshotPayloadSerializer,
    UpdateTodaysInventorySerializer,
)


class GodownUpdateBagStockView(AndroidGodownBaseView):
    """Record today's sealed-bag count from the godown floor (godown manager only)."""

    serializer_class = UpdateTodaysInventorySerializer

    def _resolve_counts(self, serializer) -> dict:
        """Map validated packaging public_ids to packaging instances.

        Mirrors ``UpdateTodaysInventoryView._resolve_counts``: confirms every
        named packaging exists, is not soft-deleted and belongs to a usable
        product, so an Android count is refused for exactly the same reasons a
        web count is.
        """
        counts = serializer.validated_data["counts"]
        ids = set(counts)
        packagings = {
            p.public_id: p
            for p in ProductPackaging.objects.select_related("product").filter(public_id__in=ids)
        }
        unknown = ids - set(packagings)
        if unknown:
            raise serializers.ValidationError(
                {"counts": f"Unknown product packagings: {', '.join(sorted(unknown))}."}
            )
        frozen = sorted(p.product.name for p in packagings.values() if not p.product.is_usable)
        if frozen:
            raise serializers.ValidationError(
                {
                    "counts": (
                        "Stock cannot be counted for unusable product(s): "
                        + ", ".join(dict.fromkeys(frozen))
                        + "."
                    )
                }
            )
        return {packagings[pid]: value for pid, value in counts.items()}

    @extend_schema(
        operation_id="android_api_v1_godown_update_bag_stock",
        summary="Replace today's entire sealed-bag stock count",
        description=(
            "Sealed-bag counts only: every active packaging of a usable product "
            "receives a snapshot row for today, and packagings absent from "
            "``counts`` are recorded as zero bags. Packagings of an unusable "
            "product cannot be counted (naming one is a 400); their last figure "
            "is carried forward. Loose packets are not accepted here -- record them "
            "at ``/android/api/v1/godown/update-sample-packet-stock``."
        ),
        request=UpdateTodaysInventorySerializer,
        responses={200: SnapshotPayloadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Whole-day bag count",
                value={
                    "counts": {
                        "PP-A1B2C3D4E0F1": 12,
                        "PP-A1B2C3D4E0F2": 0,
                    }
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request: Request) -> Response:
        serializer = UpdateTodaysInventorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provided = self._resolve_counts(serializer)

        full_counts = {packaging: provided.get(packaging, 0) for packaging in usable_packagings()}  # noqa: C420 -- provided.get() varies per key, not a constant fill
        try:
            # Packagings of an unusable product cannot be counted; carry their last
            # figure forward so freezing a product never moves its stock.
            snapshots = InventoryOperations.record_stock_counts(
                counts=full_counts, actor=request.user, carry_frozen=True
            )
        except ValueError as exc:
            raise serializers.ValidationError({"counts": str(exc)}) from None
        return Response(
            [InventoryOperations.snapshot_payload(s) for s in snapshots],
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="android_api_v1_godown_update_bag_stock_partial",
        summary="Partially update today's sealed-bag stock count",
        description=(
            "Sealed-bag counts only: only the packagings named in ``counts`` are "
            "written; the rest of today's rows are left as they are. Loose "
            "packets are not accepted here -- record them at "
            "``/android/api/v1/godown/update-sample-packet-stock``."
        ),
        request=UpdateTodaysInventorySerializer,
        responses={200: SnapshotPayloadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Partial bag count",
                value={"counts": {"PP-A1B2C3D4E0F1": 12}},
                request_only=True,
            ),
        ],
    )
    def patch(self, request: Request) -> Response:
        serializer = UpdateTodaysInventorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        counts = self._resolve_counts(serializer)
        try:
            snapshots = InventoryOperations.record_stock_counts(
                counts=counts, actor=request.user, carry_forward=True
            )
        except ValueError as exc:
            raise serializers.ValidationError({"counts": str(exc)}) from None
        return Response(
            [InventoryOperations.snapshot_payload(s) for s in snapshots],
            status=status.HTTP_200_OK,
        )
