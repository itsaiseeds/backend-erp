"""Product transfer endpoint: ``POST /api/sales-admin/transfer-product``.

Moves raw material that is already in stock from one product to another of the
same crop, so leftover kilograms are re-homed instead of written off: send
``{"source_product": "P-...", "target_product": "P-...", "quantity_kg": 55}``
(the products' public ids) and 55 kg leave the source (45 kg stay, if it had 100)
and arrive on the target.

Only an application Admin may call it, and only one allowed to change inward
material (the same gate as booking or deleting a lot). The only stock check is
``quantity_kg <= available_kg`` of the source (the raw-material stock screen's
figure); bags or packets in stock, reservations and open orders never block it.
More than is available is a 400, as is a crop mismatch or a frozen product.
How the lots are moved, and what is refused, is in
``InwardOperations.transfer_raw_material``.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator import InventoryOperations
from aggregator.InwardOperations import (
    assert_can_change_inward,
    inward_raw_material_payload,
    transfer_raw_material,
)
from aggregator.models import InwardRawMaterial
from api.admin import AdminApiView
from api.inward_serializers import TransferProductResponseSerializer, TransferProductSerializer


def _side(product) -> dict:
    return {
        "public_id": product.public_id,
        "name": product.name,
        "available_kg": str(InventoryOperations.raw_available_kg(product)),
    }


class TransferProductView(AdminApiView):
    """Transfer raw material from one product to another of the same crop (app admin only)."""

    serializer_class = TransferProductSerializer
    admin_required = True

    @extend_schema(
        operation_id="sales_admin_transfer_product",
        summary="Transfer raw material from one product to another of the same crop",
        request=TransferProductSerializer,
        responses={200: TransferProductResponseSerializer},
    )
    def post(self, request: Request):
        assert_can_change_inward(request.user)
        return transfer_product(request)


def transfer_product(request: Request) -> Response:
    """Validate the body, run the transfer and build the response.

    Shared by this view and the godown manager's
    ``android.api.v1.GodownTransferProductView``.
    """
    serializer = TransferProductSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    source, target = data["source_product"], data["target_product"]
    lots = transfer_raw_material(
        source=source,
        target=target,
        quantity_kg=data["quantity_kg"],
        actor=request.user,
    )
    booked = InwardRawMaterial.objects.select_related(
        "product", "party", "status", "created_by", "return_order__order", "lab_testing"
    ).filter(pk__in=[lot.pk for lot in lots])
    return Response(
        {
            "transferred_kg": str(data["quantity_kg"]),
            "source": _side(source),
            "target": _side(target),
            "target_lots": [inward_raw_material_payload(lot) for lot in booked.order_by("pk")],
        }
    )
