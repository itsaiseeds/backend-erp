"""Inward raw material update/delete endpoint: ``PATCH``/``DELETE``.

Path: ``/api/sales-admin/inward-raw-material/<public_id>``.

Two jobs live here:

* **Record the lifecycle.** ``PATCH`` fills in ``lab_sampling_date`` and moves
  a lot between ``lab_testing`` and ``in_use`` (both ways; see
  ``InwardOperations.ALLOWED_RAW_STATUS_TRANSITIONS``). Flipping to ``in_use``
  stamps ``effective_date`` with today; reverting to ``lab_testing`` clears the
  date. Together the stamp + status are what start and stop the lot counting
  toward ``raw-material-stock``.
* **Correct a booking.** ``product`` / ``party`` / ``quantity_kg`` are
  immutable once a lot exists; a wrong amount is removed with ``DELETE``
  (soft) and re-booked. ``DELETE`` is the only corrective verb.

Both a revert to ``lab_testing`` and a ``DELETE`` are refused (400) when the
lot's kilograms are already packed into a bag or sample-packet count --
see ``InwardOperations.assert_raw_lot_removable``.

Soft-deleted lots are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.InwardOperations import (
    assert_raw_lot_removable,
    assert_raw_status_transition,
    inward_raw_material_payload,
    today,
)
from aggregator.models import InwardRawMaterial, InwardRawMaterialStatus
from api.admin import AdminApiView

from .InwardRawMaterialsView import InwardRawMaterialPayloadSerializer


class UpdateInwardRawMaterialSerializer(serializers.Serializer):
    """Request validation for updating a raw-material lot (all fields optional).

    Only ``lab_sampling_date`` and ``status`` are accepted: flipping to
    ``in_use`` stamps the effective date with today, reverting to
    ``lab_testing`` clears it, and ``product`` / ``party`` / ``quantity_kg``
    are immutable. Any unknown key is ignored.
    """

    lab_sampling_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=InwardRawMaterialStatus.choices, required=False
    )

    def validate(self, attrs):
        if self.instance is None:
            return attrs

        requested_status = attrs.get("status", self.instance.status)

        # A status flip may only follow the allowed transitions; sending the
        # current status again is a no-op.
        if requested_status != self.instance.status:
            try:
                assert_raw_status_transition(self.instance.status, requested_status)
            except ValueError as exc:
                raise serializers.ValidationError({"status": str(exc)}) from None

        # Flipping into ``in_use`` stamps the effective date with today -- the
        # user never types it, and stamped + in_use is what stock reads count.
        # Reverting to ``lab_testing`` clears the date so the lot drops back
        # out of stock. Both keys are undeclared (never user input): the view
        # below applies them from validated_data like any declared field.
        if (
            self.instance.status != InwardRawMaterialStatus.IN_USE
            and requested_status == InwardRawMaterialStatus.IN_USE
        ):
            attrs["effective_date"] = today()
        elif (
            self.instance.status == InwardRawMaterialStatus.IN_USE
            and requested_status != InwardRawMaterialStatus.IN_USE
        ):
            # Reverting out of in_use removes this lot's kilograms from the
            # raw pool -- refuse it if bags or sample packets are already
            # packed from them.
            try:
                assert_raw_lot_removable(self.instance)
            except ValueError as exc:
                raise serializers.ValidationError({"status": str(exc)}) from None
            attrs["effective_date"] = None
        return attrs


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
        entry = get_object_or_404(InwardRawMaterial.objects.all(), public_id=public_id)

        serializer = UpdateInwardRawMaterialSerializer(
            instance=entry, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        for field in ("lab_sampling_date", "effective_date", "status"):
            if field in serializer.validated_data:
                setattr(entry, field, serializer.validated_data[field])
        entry.save()
        return Response(inward_raw_material_payload(entry))

    @extend_schema(
        summary="Delete an inward raw-material lot",
        responses={204: None},
    )
    def delete(self, request, public_id: str):
        entry = get_object_or_404(InwardRawMaterial.objects.all(), public_id=public_id)
        try:
            assert_raw_lot_removable(entry)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from None
        entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
