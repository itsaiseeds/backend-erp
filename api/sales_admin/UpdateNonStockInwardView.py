"""Non-stock inward edit/delete endpoint: ``PATCH`` / ``DELETE`` on one entry.

Path: ``/api/sales-admin/non-stock-inward/<public_id>``.

``PATCH`` corrects any of the entry's fields (send only what changed; at least
one). ``DELETE`` soft-deletes it. Both need a superuser or an admin holding
``Admin.can_update_stock_count`` (``assert_can_change_inward``). The entry
moves no stock, so neither is ever refused for stock reasons. Soft-deleted
entries are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.InwardOperations import assert_can_change_inward
from aggregator.models import NonStockInward
from api.admin import AdminApiView

from .NonStockInwardsView import (
    NonStockInwardFieldsSerializer,
    NonStockInwardPayloadSerializer,
    non_stock_inward_payload,
)


class UpdateNonStockInwardSerializer(NonStockInwardFieldsSerializer):
    """Request validation for a partial edit (every field optional, at least one)."""

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Send at least one of name, description, company_name, price, "
                "quantity, unit."
            )
        return attrs


class UpdateNonStockInwardView(AdminApiView):
    """Edit (PATCH) or soft-delete (DELETE) a non-stock inward entry (stock admins)."""

    serializer_class = UpdateNonStockInwardSerializer
    admin_required = True

    @extend_schema(
        summary="Edit a non-stock inward entry",
        request=UpdateNonStockInwardSerializer,
        responses={200: NonStockInwardPayloadSerializer},
    )
    def patch(self, request, public_id: str):
        assert_can_change_inward(request.user)
        entry = get_object_or_404(
            NonStockInward.objects.select_related("created_by"), public_id=public_id
        )
        serializer = UpdateNonStockInwardSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(entry, field, value)
        entry.save()
        return Response(non_stock_inward_payload(entry))

    @extend_schema(summary="Delete a non-stock inward entry", responses={204: None})
    def delete(self, request, public_id: str):
        assert_can_change_inward(request.user)
        entry = get_object_or_404(NonStockInward.objects.all(), public_id=public_id)
        entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
