"""Rejected lots of one party: ``GET /api/sales-admin/party-rejected-lots/<party_id>``.

The picker behind booking a rejected order: every live, rejected, dated lot the
party supplied, with how much of it earlier rejected orders already hold. Rows
with nothing left (``remaining_kg`` 0) are still listed. Read only -- it moves
no stock figure. 404 when the party is missing or deleted.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.models import Party
from api.admin import AdminApiView


class _PartyRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class _ProductRefSerializer(serializers.Serializer):
    public_id = serializers.CharField()
    name = serializers.CharField()


class _LabTestSerializer(serializers.Serializer):
    public_id = serializers.CharField()
    result = serializers.CharField(allow_null=True)
    comment = serializers.CharField(allow_blank=True)
    tested_at = serializers.DateTimeField(allow_null=True)


class PartyRejectedLotSerializer(serializers.Serializer):
    """Output shape for one rejected lot."""

    inward_raw_material_public_id = serializers.CharField()
    party = _PartyRefSerializer()
    farmer_name = serializers.CharField()
    product = _ProductRefSerializer()
    lot_no = serializers.CharField()
    quantity_kg = serializers.CharField()
    booked_kg = serializers.CharField()
    remaining_kg = serializers.CharField()
    inward_date = serializers.DateTimeField()
    rejected_on = serializers.DateField()
    lab_sampling_date = serializers.DateField(allow_null=True)
    lab_test = _LabTestSerializer(allow_null=True)


class GetPartyRejectedLotsView(AdminApiView):
    """List a party's rejected lots (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="List a party's rejected lots with booked and remaining kg",
        parameters=[OpenApiParameter("party_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
        responses={200: PartyRejectedLotSerializer(many=True)},
    )
    def get(self, request: Request, party_id: int) -> Response:
        party = get_object_or_404(Party, pk=party_id)
        lots = list(
            InventoryOperations.bookable_rejected_lots()
            .filter(party=party)
            .select_related("party", "product", "lab_testing")
            .order_by("-effective_date", "-id")
        )
        booked = InventoryOperations.rejected_lot_booked_kg(lot.pk for lot in lots)
        rows = []
        for lot in lots:
            booked_kg = booked.get(lot.pk, 0)
            test = lot.lab_testing
            rows.append(
                {
                    "inward_raw_material_public_id": lot.public_id,
                    "party": {"id": party.id, "name": party.name},
                    "farmer_name": lot.farmer_name,
                    "product": {"public_id": lot.product.public_id, "name": lot.product.name},
                    "lot_no": lot.lot_no,
                    "quantity_kg": str(lot.quantity_kg),
                    "booked_kg": str(booked_kg),
                    "remaining_kg": str(lot.quantity_kg - booked_kg),
                    "inward_date": lot.created_at.isoformat(),
                    "rejected_on": lot.effective_date.isoformat(),
                    "lab_sampling_date": (
                        lot.lab_sampling_date.isoformat() if lot.lab_sampling_date else None
                    ),
                    "lab_test": (
                        {
                            "public_id": test.public_id,
                            "result": test.result,
                            "comment": test.comment,
                            "tested_at": test.tested_at.isoformat() if test.tested_at else None,
                        }
                        if test
                        else None
                    ),
                }
            )
        return Response(rows)
