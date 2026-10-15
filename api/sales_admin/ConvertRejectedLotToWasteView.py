"""Convert a rejected lot to waste.

Path: ``POST /api/sales-admin/inward-raw-material/<IR-id>/convert-to-waste``.

Writes the **whole** of a lab-rejected lot off as waste: a ``RawMaterialWaste``
row linked to the lot is created and returned (201). Body: ``{"reason": "..."}``
(optional). The lot keeps its Rejected status but counts as wasted, so it leaves
the rejected stock and cannot be booked on a rejected order. Usable stock does
not move. Refused (400) when the lot is not a reached rejected lot, is already
converted, or has kg on a rejected order. The reverse is ``DELETE`` on the
returned waste row (``UpdateRawMaterialWasteView``).

Only an application Admin may call it; the godown manager has the same action
at ``godown/inward-raw-material/<IR-id>/convert-to-waste``.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.InwardOperations import raw_waste_payload
from aggregator.models import InwardRawMaterial, RawMaterialWaste
from api.admin import AdminApiView
from api.inward_serializers import (
    ConvertRejectedLotToWasteSerializer,
    RawMaterialWastePayloadSerializer,
)


def convert_to_waste(request: Request, public_id: str) -> Response:
    """Validate the body, convert the lot and build the 201 response.

    Shared by this view and the godown manager's
    ``android.api.v1.ConvertGodownRejectedLotToWasteView``.
    """
    lot = get_object_or_404(InwardRawMaterial.objects.all(), public_id=public_id)
    serializer = ConvertRejectedLotToWasteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    waste = InventoryOperations.convert_rejected_lot_to_waste(
        lot, reason=serializer.validated_data["reason"], actor=request.user
    )
    waste = RawMaterialWaste.objects.select_related(
        "product", "created_by", "inward_raw_material"
    ).get(pk=waste.pk)
    return Response(raw_waste_payload(waste), status=status.HTTP_201_CREATED)


class ConvertRejectedLotToWasteView(AdminApiView):
    """Write a whole rejected lot off as waste (app admin only)."""

    serializer_class = ConvertRejectedLotToWasteSerializer
    admin_required = True

    @extend_schema(
        operation_id="sales_admin_convert_rejected_lot_to_waste",
        summary="Convert a rejected lot to waste",
        request=ConvertRejectedLotToWasteSerializer,
        responses={201: RawMaterialWastePayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return convert_to_waste(request, public_id)
