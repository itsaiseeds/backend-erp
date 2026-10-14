"""Godown product transfer: POST ``godown/transfer-product``.

The Android counterpart of ``api.sales_admin.TransferProductView``: same request
(``{"source_product": "P-...", "target_product": "P-...", "quantity_kg": "5"}``),
response and rules (``InwardOperations.transfer_raw_material``) -- raw material
available in the source product moves to another of the same crop.
Godown-manager token only; like the godown inward endpoints it is not gated by
the admin's ``can_update_stock_count``.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from android.api.base import AndroidGodownBaseView
from api.inward_serializers import TransferProductResponseSerializer, TransferProductSerializer
from api.sales_admin.TransferProductView import transfer_product


class GodownTransferProductView(AndroidGodownBaseView):
    """Transfer raw material from one product to another of the same crop (godown manager only)."""

    serializer_class = TransferProductSerializer

    @extend_schema(
        operation_id="android_api_v1_godown_transfer_product",
        summary="Transfer raw material from one product to another of the same crop",
        request=TransferProductSerializer,
        responses={200: TransferProductResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        return transfer_product(request)
