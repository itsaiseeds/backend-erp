"""Loose-stock count endpoint: ``POST``/``PATCH`` ``/api/sales-admin/update-loose-stock``.

Loose stock is stock **in a packet but not in a bag**. It is identified by
``(product, packet_weight)`` and nothing else -- a product packed as both
1kg x 20 and 1kg x 30 has one pool of loose 1kg packets, not two -- so the
payload is a **list** of lines rather than a map keyed by a single public id.

Only an application Admin holding ``Admin.can_update_stock_count`` may write a
count (also enforced by ``InventoryOperations._assert_can_update_stock_count``).

Unlike the daily bag count this is **optional**: nothing requires it to be
written daily, or at all, and a missing loose count never blocks order
verification. Recording a count purges older *loose* rows only -- the bag
snapshot is on its own independent lifecycle and is never touched here.

``POST`` replaces the whole loose count for today: every ``(product,
packet_weight)`` pair the business packs receives a row, and pairs absent from
the payload are recorded as zero. ``PATCH`` writes only the lines named in the
payload and leaves the rest alone.
"""

from __future__ import annotations

from decimal import Decimal

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.models import Product, ProductPackaging
from api.admin import AdminApiView


class LooseCountLineSerializer(serializers.Serializer):
    """One submitted loose line: a product, a packet weight and a packet count."""

    product = serializers.CharField(help_text="Product public_id (``P-…``).")
    packet_weight = serializers.DecimalField(max_digits=8, decimal_places=3, min_value=0)
    packets = serializers.IntegerField(min_value=0)


class UpdateLooseStockSerializer(serializers.Serializer):
    """Request validation: a list of loose lines."""

    counts = LooseCountLineSerializer(
        many=True,
        error_messages={"required": "Loose stock counts are required."},
        help_text="Loose lines, one per (product, packet_weight) pair.",
    )


class LooseStockProductRefSerializer(serializers.Serializer):
    """Output shape for the ``product`` reference inside a loose line."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class LooseStockPayloadSerializer(serializers.Serializer):
    """Output shape for one recorded loose line."""

    public_id = serializers.CharField()
    snapshot_date = serializers.DateField()
    product = LooseStockProductRefSerializer()
    packet_weight = serializers.DecimalField(max_digits=8, decimal_places=3)
    packets = serializers.IntegerField(min_value=0)
    total_weight = serializers.DecimalField(max_digits=11, decimal_places=3)
    reserved = serializers.IntegerField()
    consumed = serializers.IntegerField()
    available = serializers.IntegerField()


def packable_pairs() -> dict[tuple[str, Decimal], tuple[Product, Decimal]]:
    """Every ``(product, packet_weight)`` pair the business actually packs.

    Taken from the active packagings: a loose packet only exists in a weight
    something is packed in, so this is the universe of valid loose lines and
    the zero-fill set for a ``POST``.
    """
    pairs: dict[tuple[str, Decimal], tuple[Product, Decimal]] = {}
    for packaging in ProductPackaging.objects.select_related("product"):
        product = packaging.product
        pairs[(product.public_id, packaging.packet_weight)] = (
            product,
            packaging.packet_weight,
        )
    return pairs


class UpdateLooseStockView(AdminApiView):
    """Record the loose-packet count (stock-update admin only)."""

    admin_required = True
    serializer_class = UpdateLooseStockSerializer

    def _resolve_counts(self, serializer) -> dict:
        """Map validated lines to ``{(product, packet_weight): packets}``.

        Rejects a pair the business does not pack, and a pair named twice in
        one payload (which would otherwise let the last line silently win).
        """
        lines = serializer.validated_data["counts"]
        valid = packable_pairs()

        counts = {}
        unknown, duplicates = [], []
        for line in lines:
            key = (line["product"], line["packet_weight"])
            if key not in valid:
                unknown.append(f"{key[0]} @ {key[1]}kg")
                continue
            resolved = valid[key]
            if resolved in counts:
                duplicates.append(f"{key[0]} @ {key[1]}kg")
                continue
            counts[resolved] = line["packets"]

        errors = []
        if unknown:
            errors.append(
                "No packaging exists for: " + ", ".join(sorted(unknown)) + "."
            )
        if duplicates:
            errors.append(
                "Repeated product/packet-weight pairs: "
                + ", ".join(sorted(duplicates))
                + "."
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
        summary="Replace the whole loose-stock count",
        description=(
            "Every (product, packet_weight) pair the business packs receives a "
            "loose row for today. Pairs absent from ``counts`` are recorded as "
            "zero packets. Does not touch the sealed-bag snapshot."
        ),
        request=UpdateLooseStockSerializer,
        responses={200: LooseStockPayloadSerializer(many=True)},
    )
    def post(self, request):
        serializer = UpdateLooseStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provided = self._resolve_counts(serializer)

        full_counts = {
            pair: provided.get(pair, 0) for pair in packable_pairs().values()
        }
        snapshots = InventoryOperations.record_loose_stocks(
            counts=full_counts, actor=request.user
        )
        return self._respond(snapshots)

    @extend_schema(
        summary="Partially update the loose-stock count",
        description=(
            "Only the pairs named in ``counts`` are written; every other loose "
            "row is left as it is."
        ),
        request=UpdateLooseStockSerializer,
        responses={200: LooseStockPayloadSerializer(many=True)},
    )
    def patch(self, request):
        serializer = UpdateLooseStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        counts = self._resolve_counts(serializer)
        snapshots = InventoryOperations.record_loose_stocks(
            counts=counts, actor=request.user
        )
        return self._respond(snapshots)
