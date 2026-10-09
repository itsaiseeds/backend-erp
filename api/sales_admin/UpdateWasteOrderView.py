"""Waste-order update endpoint: ``PATCH /api/sales-admin/edit-waste-order/<public_id>``.

``edit-custom-order`` for a waste order: the same rules (client fixed, address by
link id, comments appended, ``items`` a full declarative replacement, CONFIRMED
only) with kg lines keyed by ``product_public_id``. A raised quantity or an added
product must be covered by the product's unused waste, the kilograms the order
already holds counting towards it; a shortfall is a 400 and nothing is written.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import (
    assert_order_kind,
    sync_waste_order_items,
)
from api.custom_order_serializers import CustomOrderDetailPayloadSerializer

from .CreateWasteOrderView import (
    WasteOrderItemWriteSerializer,
    resolve_waste_order_items,
    validate_waste_order_item_list,
)
from .CustomOrderView import CUSTOM_ORDER_PUBLIC_ID_PARAMETER
from .UpdateCustomOrderView import UpdateCustomOrderSerializer, UpdateCustomOrderView


class UpdateWasteOrderSerializer(UpdateCustomOrderSerializer):
    """Request validation for a waste-order update -- every field optional."""

    items = WasteOrderItemWriteSerializer(many=True, required=False)

    def validate_items(self, value: list[dict]) -> list[dict]:
        return validate_waste_order_item_list(value)

    def resolve_items(self, items: list[dict], order) -> list[dict]:
        return resolve_waste_order_items(items, order)


class UpdateWasteOrderView(UpdateCustomOrderView):
    """Update a waste order, including its kg lines (app admin only)."""

    serializer_class = UpdateWasteOrderSerializer

    def assert_kind(self, order) -> None:
        assert_order_kind(order, True, "edit")

    def sync_items(self, order, items, actor) -> None:
        sync_waste_order_items(order, items, actor)

    @extend_schema(
        summary="Update a waste order (including its items)",
        request=UpdateWasteOrderSerializer,
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={200: CustomOrderDetailPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        return super().patch(request, public_id)

