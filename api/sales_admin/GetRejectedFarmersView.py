"""Rejected-lot pickers for booking a rejected order, one level at a time.

``GET /api/sales-admin/rejected-orders/<party_id>`` -- the farmers of a party
who have at least one rejected lot to sell, with how much is left.

``GET /api/sales-admin/rejected-orders/<party_id>/<farmer_name>`` -- that
farmer's rejected lots (the rows ``create-rejected-order`` books against, each
with its ``inward_raw_material_public_id`` and ``lot_no``).

A lot counts when it is live, Rejected and its rejected date has been reached.
A lot with nothing left (``remaining_kg`` 0) is still listed. ``farmer_name`` is
free text on the lot, matched exactly (percent-encode it in the URL). Both are
read only -- no stock figure moves. 404 when the party is missing or deleted;
a farmer with no such lot is an empty list.
"""

from __future__ import annotations

from decimal import Decimal

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.models import Party
from api.admin import AdminApiView

from .GetPartyRejectedLotsView import PartyRejectedLotSerializer, rejected_lot_rows

PARTY_ID_PARAMETER = OpenApiParameter("party_id", OpenApiTypes.INT, OpenApiParameter.PATH)


class RejectedFarmerSerializer(serializers.Serializer):
    """Output shape for one farmer of a party."""

    farmer_name = serializers.CharField()
    lot_count = serializers.IntegerField()
    quantity_kg = serializers.CharField()
    remaining_kg = serializers.CharField()


def _party_lots(party: Party):
    return (
        InventoryOperations.bookable_rejected_lots()
        .filter(party=party)
        .select_related("party", "product", "lab_testing")
        .order_by("-effective_date", "-id")
    )


class GetRejectedFarmersView(AdminApiView):
    """Farmers of a party with at least one rejected lot (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="List a party's farmers who have a rejected lot",
        parameters=[PARTY_ID_PARAMETER],
        responses={200: RejectedFarmerSerializer(many=True)},
    )
    def get(self, request: Request, party_id: int) -> Response:
        party = get_object_or_404(Party, pk=party_id)
        lots = list(_party_lots(party))
        booked = InventoryOperations.rejected_lot_booked_kg(lot.pk for lot in lots)
        farmers: dict[str, dict] = {}
        for lot in lots:
            row = farmers.setdefault(
                lot.farmer_name,
                {
                    "farmer_name": lot.farmer_name,
                    "lot_count": 0,
                    "quantity_kg": Decimal("0.000"),
                    "remaining_kg": Decimal("0.000"),
                },
            )
            row["lot_count"] += 1
            row["quantity_kg"] += lot.quantity_kg
            row["remaining_kg"] += lot.quantity_kg - booked.get(lot.pk, Decimal("0.000"))
        rows = [
            {
                **row,
                "quantity_kg": str(row["quantity_kg"]),
                "remaining_kg": str(row["remaining_kg"]),
            }
            for row in sorted(farmers.values(), key=lambda row: row["farmer_name"].lower())
        ]
        return Response(rows)


class GetRejectedFarmerLotsView(AdminApiView):
    """One farmer's rejected lots within a party (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="List a farmer's rejected lots (lot numbers) within a party",
        parameters=[
            PARTY_ID_PARAMETER,
            OpenApiParameter("farmer_name", OpenApiTypes.STR, OpenApiParameter.PATH),
        ],
        responses={200: PartyRejectedLotSerializer(many=True)},
    )
    def get(self, request: Request, party_id: int, farmer_name: str) -> Response:
        party = get_object_or_404(Party, pk=party_id)
        lots = list(_party_lots(party).filter(farmer_name=farmer_name))
        return Response(rejected_lot_rows(party, lots))
