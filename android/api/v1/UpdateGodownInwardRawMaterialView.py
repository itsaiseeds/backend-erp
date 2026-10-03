"""Godown inward raw-material lot: PATCH/DELETE ``godown/inward-raw-material/<public_id>``.

Path: ``/android/api/v1/godown/inward-raw-material/<public_id>``.

The Android counterpart of ``api.sales_admin.UpdateInwardRawMaterialView``. The
lifecycle (``assert_raw_status_transition``), the ``effective_date`` stamping,
the packed-stock refusals (``assert_raw_lot_removable``) and the pool locking
(``locked_raw_lot``) are the shared ``InwardOperations`` / serializer logic --
reverting or deleting an ``In Use`` lot whose kilograms are already packed is
a 400. ``DELETE`` (soft) is how a mistyped booking is corrected: ``product`` /
``party`` / ``quantity_kg`` are immutable.

Godown-manager token only; soft-deleted lots are a 404.
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.InwardOperations import (
    inward_raw_material_payload,
    locked_raw_lot,
    update_raw_lot,
)
from aggregator.models import InwardRawMaterial
from android.api.base import AndroidGodownBaseView
from api.inward_serializers import (
    InwardRawMaterialPayloadSerializer,
    UpdateInwardRawMaterialSerializer,
)


class UpdateGodownInwardRawMaterialView(AndroidGodownBaseView):
    """Update the lifecycle or soft-delete a raw-material lot (godown manager only)."""

    serializer_class = UpdateInwardRawMaterialSerializer

    @extend_schema(
        summary="Update an inward raw-material lot",
        request=UpdateInwardRawMaterialSerializer,
        responses={200: InwardRawMaterialPayloadSerializer},
    )
    def patch(self, request: Request, public_id: str) -> Response:
        with transaction.atomic():
            entry = locked_raw_lot(
                InwardRawMaterial.objects.select_related(
                    "product", "party", "status", "created_by"
                ),
                public_id,
            )

            serializer = UpdateInwardRawMaterialSerializer(
                instance=entry, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            update_raw_lot(entry, serializer.validated_data, request.user)
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
