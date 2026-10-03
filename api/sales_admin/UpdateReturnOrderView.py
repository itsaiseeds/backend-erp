"""Return update endpoint: ``PATCH /api/sales-admin/edit-return-order/<public_id>``.

A sales admin corrects a return's lines and date. The body is the one the Android
``POST return-order/<order_public_id>`` takes: an optional ``return_date`` and
``items``, a **full declarative replacement** -- a line left out is removed.

**Only a PENDING return is editable**, and the same rules as creating one apply:
the order must still be DISPATCHED or DELIVERED, and no pair may exceed the
packets the challan carried. A breach is a 400 and nothing is written.
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ReturnOrderOperations import return_order_payload, update_return_order
from api.admin import AdminApiView
from api.return_order_serializers import ReturnOrderPayloadSerializer, ReturnOrderWriteSerializer

from .ReturnOrderTransitionView import (
    RETURN_PUBLIC_ID_PARAMETER,
    get_locked_return_order,
    return_order_queryset,
)


class UpdateReturnOrderView(AdminApiView):
    """Replace a pending return's lines (app admin only)."""

    serializer_class = ReturnOrderWriteSerializer
    admin_required = True

    @extend_schema(
        summary="Edit a pending return (including its items)",
        request=ReturnOrderWriteSerializer,
        parameters=[RETURN_PUBLIC_ID_PARAMETER],
        responses={200: ReturnOrderPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        serializer = ReturnOrderWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            ret = get_locked_return_order(public_id)
            update_return_order(
                ret,
                return_date=data.get("return_date"),
                items=data["resolved_items"],
                actor=request.user,
            )
        return Response(return_order_payload(return_order_queryset().get(pk=ret.pk)))
