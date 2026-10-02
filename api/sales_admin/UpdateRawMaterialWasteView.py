"""Raw material waste delete endpoint: ``DELETE`` on ``raw-material-waste/<public_id>``.

Path: ``/api/sales-admin/raw-material-waste/<public_id>``.

A waste row is immutable: a wrong entry is removed with ``DELETE`` (soft) and,
if still needed, re-recorded. Deleting gives the kilograms back to the
product's unpacked raw pool, which can only raise availability, so it is never
refused. Soft-deleted rows are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from aggregator.models import RawMaterialWaste
from api.admin import AdminApiView


class UpdateRawMaterialWasteView(AdminApiView):
    """Soft-delete a raw-material waste row (app admin only)."""

    admin_required = True

    @extend_schema(summary="Delete a raw-material waste row", responses={204: None})
    def delete(self, request, public_id: str):
        entry = get_object_or_404(RawMaterialWaste.objects.all(), public_id=public_id)
        entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
