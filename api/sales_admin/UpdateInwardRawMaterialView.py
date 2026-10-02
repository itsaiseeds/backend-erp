"""Inward raw material update/delete endpoint: ``PATCH``/``DELETE``.

Path: ``/api/sales-admin/inward-raw-material/<public_id>``.

Two jobs live here:

* **Record the lifecycle.** ``PATCH`` fills in ``lab_sampling_date`` and moves
  a lot between ``Lab Testing`` and either ``In Use`` or ``Rejected`` (both
  ways; see ``InwardOperations.ALLOWED_RAW_STATUS_TRANSITIONS``).
  ``Lab Testing`` is the hub: ``In Use`` and ``Rejected`` are never a direct
  move between each other. Flipping into either dated status stamps
  ``effective_date`` with today; reverting either to ``Lab Testing`` clears
  that date and re-stamps ``lab_sampling_date`` with today, as the lot is back
  with the lab as of today. Together the stamp + status are what start and
  stop the lot counting toward ``raw-material-stock``'s ``incoming_kg`` or
  ``rejected_kg``.
* **Correct a booking.** ``product`` / ``party`` / ``lot_no`` / ``quantity_kg``
  are immutable once a lot exists; a wrong amount is removed with ``DELETE``
  (soft) and re-booked. ``DELETE`` is the only corrective verb.

A revert from ``In Use`` to ``Lab Testing`` and a ``DELETE`` of an ``In Use``
lot are refused (400) when the lot's kilograms are already packed into a bag
or sample-packet count -- see ``InwardOperations.assert_raw_lot_removable``.
A ``Rejected`` lot was never packable, so reverting or deleting one is never
refused on those grounds.

Soft-deleted lots are never found (404).
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from aggregator.InwardOperations import (
    inward_raw_material_payload,
    locked_raw_lot,
    update_raw_lot,
)
from aggregator.models import InwardRawMaterial
from api.admin import AdminApiView
from api.inward_serializers import (
    InwardRawMaterialPayloadSerializer,
    UpdateInwardRawMaterialSerializer,
)


class UpdateInwardRawMaterialView(AdminApiView):
    """Update the lifecycle or soft-delete a raw-material lot (app admin only)."""

    serializer_class = UpdateInwardRawMaterialSerializer
    admin_required = True

    @extend_schema(
        summary="Update an inward raw-material lot",
        request=UpdateInwardRawMaterialSerializer,
        responses={200: InwardRawMaterialPayloadSerializer},
    )
    def patch(self, request, public_id: str):
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
    def delete(self, request, public_id: str):
        with transaction.atomic():
            entry = locked_raw_lot(
                InwardRawMaterial.objects.select_related("status"), public_id
            )
            # Refused by InwardRawMaterial.guard_soft_delete (a 400) when the
            # lot's kilograms are already packed.
            entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
