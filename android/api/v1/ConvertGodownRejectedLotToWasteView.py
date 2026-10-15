"""Godown convert-to-waste: POST ``godown/inward-raw-material/<public_id>/convert-to-waste``.

The Android counterpart of ``api.sales_admin.ConvertRejectedLotToWasteView``,
with the same body, response (201, the waste row) and rules. The reverse is
``DELETE godown/raw-material-waste/<public_id>``. Godown-manager token only.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from android.api.base import AndroidGodownBaseView
from api.inward_serializers import (
    ConvertRejectedLotToWasteSerializer,
    RawMaterialWastePayloadSerializer,
)
from api.sales_admin.ConvertRejectedLotToWasteView import convert_to_waste


class ConvertGodownRejectedLotToWasteView(AndroidGodownBaseView):
    """Write a whole rejected lot off as waste (godown manager only)."""

    serializer_class = ConvertRejectedLotToWasteSerializer

    @extend_schema(
        operation_id="android_api_v1_godown_convert_rejected_lot_to_waste",
        summary="Convert a rejected lot to waste",
        request=ConvertRejectedLotToWasteSerializer,
        responses={201: RawMaterialWastePayloadSerializer},
    )
    def post(self, request: Request, public_id: str) -> Response:
        return convert_to_waste(request, public_id)
