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
from django.db.models import QuerySet
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.InventoryOperations import lock_raw_pools
from aggregator.InwardOperations import (
    DATED_RAW_STATUSES,
    assert_raw_lot_removable,
    assert_raw_status_transition,
    inward_raw_material_payload,
    raw_status_of,
    status_row_for,
    today,
)
from aggregator.models import InwardRawMaterial, InwardRawMaterialStatus
from api.admin import AdminApiView

from .InwardRawMaterialsView import InwardRawMaterialPayloadSerializer


class UpdateInwardRawMaterialSerializer(serializers.Serializer):
    """Request validation for updating a raw-material lot (all fields optional).

    Only ``lab_sampling_date`` and ``status`` are accepted: flipping to
    ``In Use`` stamps the effective date with today, reverting to
    ``Lab Testing`` clears it, and ``product`` / ``party`` / ``quantity_kg``
    are immutable. Any unknown key is ignored.
    """

    lab_sampling_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=InwardRawMaterialStatus.choices, required=False
    )

    def validate(self, attrs):
        if self.instance is None:
            return attrs

        current_status = raw_status_of(self.instance)
        requested_status = (
            InwardRawMaterialStatus(attrs["status"]) if "status" in attrs else current_status
        )

        # A status flip may only follow the allowed transitions; sending the
        # current status again is a no-op.
        if requested_status != current_status:
            try:
                assert_raw_status_transition(current_status, requested_status)
            except ValueError as exc:
                raise serializers.ValidationError({"status": str(exc)}) from None

        # Flipping into a dated status (In Use or Rejected) stamps the
        # effective date with today -- the user never types it, and stamped +
        # that status is what the stock read counts (incoming_kg / rejected_kg
        # respectively). Reverting out of one to Lab Testing clears the date
        # so the lot drops back out of stock, and re-stamps lab_sampling_date
        # with today -- the lot is back with the lab as of today, same as a
        # fresh lot. Both keys override whatever the request sent for them
        # (undeclared/declared alike): the view below applies them from
        # validated_data like any other field.
        if (
            current_status not in DATED_RAW_STATUSES
            and requested_status in DATED_RAW_STATUSES
        ):
            attrs["effective_date"] = today()
        elif (
            current_status in DATED_RAW_STATUSES
            and requested_status not in DATED_RAW_STATUSES
        ):
            # Reverting out of In Use removes this lot's kilograms from the
            # raw pool -- refuse it if bags or sample packets are already
            # packed from them. A Rejected lot was never in that pool, so this
            # is always a no-op for it (never refused).
            try:
                assert_raw_lot_removable(self.instance)
            except ValueError as exc:
                raise serializers.ValidationError({"status": str(exc)}) from None
            attrs["effective_date"] = None
            attrs["lab_sampling_date"] = today()

        if "status" in attrs:
            attrs["status"] = status_row_for(requested_status)
        return attrs


def locked_raw_lot(queryset: QuerySet, public_id: str) -> InwardRawMaterial:
    """Load a lot with its product's raw pool locked, for a revert or delete.

    Removing a lot is checked against the raw pool (``assert_raw_lot_removable``)
    and stock counts are written against that same pool under
    ``lock_raw_pools``. Taking the same lock here, *before* the lot is read,
    stops a count and a removal from interleaving and stranding bags with no
    raw material behind them. The lot itself is then read -- and locked --
    after the pool, so its status is the one the check will act on and every
    caller acquires the rows in the same order.

    The lot's own lock is taken on the bare row and the joined load runs
    afterwards: a locking query that waited re-checks its joins against the
    changed row, so locking through the ``status`` join would drop a lot whose
    status had just changed and 404 (see ``GetOrderView.get_locked_order``).

    Must be called inside ``transaction.atomic``.
    """
    lots = InwardRawMaterial.objects.filter(public_id=public_id)
    product_id = lots.values_list("product_id", flat=True).first()
    if product_id is None:
        raise Http404("No InwardRawMaterial matches the given query.")
    lock_raw_pools([product_id])
    # Soft-deleted by a request that held the lock before us: gone, so a 404.
    pk = lots.select_for_update().values_list("pk", flat=True).first()
    if pk is None:
        raise Http404("No InwardRawMaterial matches the given query.")
    return queryset.get(pk=pk)


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
                InwardRawMaterial.objects.select_related("product", "party", "status"),
                public_id,
            )

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
        with transaction.atomic():
            entry = locked_raw_lot(
                InwardRawMaterial.objects.select_related("status"), public_id
            )
            # Refused by InwardRawMaterial.guard_soft_delete (a 400) when the
            # lot's kilograms are already packed.
            entry.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
