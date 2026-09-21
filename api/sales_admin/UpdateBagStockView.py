"""Daily stock-count endpoint: ``POST``/``PATCH`` ``/api/sales-admin/update-todays-inventory``.

Only an application Admin holding ``Admin.can_update_stock_count`` may write a
count (also enforced by ``InventoryOperations._assert_can_update_stock_count``).

This is the **sealed-bag** count only. Loose stock -- stock in a packet but not
in a bag -- is counted separately and optionally at
``/api/sales-admin/update-loose-stock``, on its own independent lifecycle:
writing a bag count here never touches a loose row.

``POST`` replaces **today's entire** count: every active packaging receives a
row for today, and packagings absent from the payload are recorded as zero.
``PATCH`` updates only the packagings named in the payload and leaves the rest
of today's rows untouched.

Either way, only the latest ``snapshot_date`` is retained -- recording today's
count purges every older bag row (see ``InventoryOperations``).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.models import ProductPackaging
from api.admin import AdminApiView


class UpdateTodaysInventorySerializer(serializers.Serializer):
    """Request validation: a map of packaging ``public_id`` → today's bag count."""

    counts = serializers.DictField(
        child=serializers.IntegerField(min_value=0),
        error_messages={"required": "Stock counts are required."},
        help_text="Map of product-packaging public_id to its bag count.",
    )


class PackagingProductRefSerializer(serializers.Serializer):
    """Output shape for the ``product`` reference inside a snapshot."""

    public_id = serializers.CharField()
    name = serializers.CharField()


class PackagingRefSerializer(serializers.Serializer):
    """Output shape for the ``packaging`` reference inside a snapshot."""

    public_id = serializers.CharField()
    product = PackagingProductRefSerializer()
    packet_weight = serializers.DecimalField(max_digits=8, decimal_places=3)
    packets = serializers.IntegerField(min_value=1)


class SnapshotPayloadSerializer(serializers.Serializer):
    """Output shape for one recorded snapshot line."""

    public_id = serializers.CharField()
    snapshot_date = serializers.DateField()
    packaging = PackagingRefSerializer()
    bags = serializers.IntegerField(min_value=0)
    total_packets = serializers.IntegerField(min_value=0)
    total_weight = serializers.DecimalField(max_digits=11, decimal_places=3)
    packets_available = serializers.IntegerField()


class UpdateTodaysInventoryView(AdminApiView):
    """Record today's physical stock count (stock-update admin only)."""

    admin_required = True
    serializer_class = UpdateTodaysInventorySerializer

    def _resolve_counts(self, serializer) -> dict:
        """Map validated packaging public_ids to packaging instances.

        ``serializer.validated_data`` holds ``{public_id: bags}``; this returns
        ``{packaging: bags}`` after confirming every named packaging exists and
        is not soft-deleted.
        """
        counts = serializer.validated_data["counts"]
        ids = set(counts)
        packagings = {
            p.public_id: p
            for p in ProductPackaging.objects.filter(public_id__in=ids)
        }
        unknown = ids - set(packagings)
        if unknown:
            raise serializers.ValidationError(
                {"counts": f"Unknown product packagings: {', '.join(sorted(unknown))}."}
            )
        return {packagings[pid]: value for pid, value in counts.items()}

    @extend_schema(
        summary="Replace today's entire stock count",
        description=(
            "Every active packaging receives a snapshot row for today. Packagings "
            "absent from ``counts`` are recorded as zero bags. Loose stock is "
            "counted separately and is not affected."
        ),
        request=UpdateTodaysInventorySerializer,
        responses={200: SnapshotPayloadSerializer(many=True)},
    )
    def post(self, request):
        serializer = UpdateTodaysInventorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provided = self._resolve_counts(serializer)

        full_counts = {
            packaging: provided.get(packaging, 0)
            for packaging in ProductPackaging.objects.all()
        }  # noqa: C420 -- provided.get() varies per key, not a constant fill
        snapshots = InventoryOperations.record_stock_counts(
            counts=full_counts, actor=request.user
        )
        return Response(
            [InventoryOperations.snapshot_payload(s) for s in snapshots],
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Partially update today's stock count",
        description=(
            "Only the packagings named in ``counts`` are written; the rest of "
            "today's rows are left as they are."
        ),
        request=UpdateTodaysInventorySerializer,
        responses={200: SnapshotPayloadSerializer(many=True)},
    )
    def patch(self, request):
        serializer = UpdateTodaysInventorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        counts = self._resolve_counts(serializer)
        snapshots = InventoryOperations.record_stock_counts(
            counts=counts, actor=request.user
        )
        return Response(
            [InventoryOperations.snapshot_payload(s) for s in snapshots],
            status=status.HTTP_200_OK,
        )
