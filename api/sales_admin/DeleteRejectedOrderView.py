"""Rejected-order delete: ``DELETE /api/sales-admin/rejected-order/<public_id>``.

Withdraws a rejected order, but only while it is DISPATCHED and only on the day
it was dispatched (IST). Its lots' kilograms become bookable again. 204 on
success; the shared ``custom-order/<public_id>`` DELETE still refuses it (it is
not CONFIRMED).
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.CustomOrderOperations import delete_rejected_order
from api.admin import AdminApiView

from .CustomOrderView import CUSTOM_ORDER_PUBLIC_ID_PARAMETER, get_locked_custom_order


class DeleteRejectedOrderView(AdminApiView):
    """Delete a rejected order dispatched today (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Delete a rejected order dispatched today",
        parameters=[CUSTOM_ORDER_PUBLIC_ID_PARAMETER],
        responses={204: None},
    )
    def delete(self, request: Request, public_id: str) -> Response:
        with transaction.atomic():
            order = get_locked_custom_order(public_id)
            delete_rejected_order(order, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
