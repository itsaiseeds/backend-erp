"""Godown inward raw-material lot: PATCH/DELETE ``godown/inward-raw-material/<public_id>``.

Path: ``/android/api/v1/godown/inward-raw-material/<public_id>``.

The Android counterpart of ``api.sales_admin.UpdateInwardRawMaterialView``, minus
the lifecycle: a godown manager books and deletes lots but never moves them
between ``Lab Testing``, ``In Use`` and ``Rejected``. A lab tester's verdict
moves a lot out of ``Lab Testing`` and an admin sends it back, so ``PATCH`` has
nothing writable here -- sending ``status`` or ``lab_sampling_date`` is a 400 --
and returns the lot unchanged. ``DELETE`` (soft) is how a mistyped booking is
corrected: ``product`` / ``party`` / ``quantity_kg`` are immutable, and deleting
an ``In Use`` lot whose kilograms are already packed is a 400
(``assert_raw_lot_removable``, ``locked_raw_lot``).

Godown-manager token only; soft-deleted lots are a 404.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import inward_raw_material_payload, locked_raw_lot
from aggregator.models import InwardRawMaterial
from android.api.base import AndroidGodownBaseView
from api.inward_serializers import (
    GodownUpdateInwardRawMaterialSerializer,
    InwardRawMaterialPayloadSerializer,
)


class UpdateGodownInwardRawMaterialView(AndroidGodownBaseView):
    """Confirm a lot unchanged or soft-delete it (godown manager only)."""

    serializer_class = GodownUpdateInwardRawMaterialSerializer

    @extend_schema(
        summary="Update an inward raw-material lot (no writable fields)",
        request=GodownUpdateInwardRawMaterialSerializer,
        responses={200: InwardRawMaterialPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        entry = get_object_or_404(
            InwardRawMaterial.objects.select_related(
                "product", "party", "status", "created_by", "return_order__order", "lab_testing"
            ),
            public_id=public_id,
        )
        # A lot an accepted return booked is owned by that return.
        entry.refuse_return_lot_change()

        serializer = GodownUpdateInwardRawMaterialSerializer(
            instance=entry, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        return Response(inward_raw_material_payload(entry))

    @extend_schema(
        summary="Delete an inward raw-material lot",
        responses={204: None},
    )
    def delete(self, request: Request, public_id: str) -> Response:
        with transaction.atomic():
            entry = locked_raw_lot(InwardRawMaterial.objects.select_related("status"), public_id)
            # Refused by InwardRawMaterial.guard_soft_delete (a 400) when the
            # lot's kilograms are already packed.
            entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
