"""Lab tester update/delete: ``PATCH``/``DELETE`` ``/api/sales-admin/lab-testers/<id>``.

Only an application Admin may update or delete a lab tester
(``admin_required`` on ``AdminApiView``, mirroring ``LabTestersView``). As
with sales people, a lab tester that belongs to an admin or a superuser may
only be touched by a superuser (403 otherwise): this endpoint writes the login
phone number.

Soft-deleted lab testers are never found (404).
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import LabTester, User
from authentication.UserOperations import (
    LabTesterPayloadSerializer,
    UpdateLabTesterSerializer,
    deactivate_if_roleless,
    lab_tester_payload,
)


def _refuse_higher_role(caller: User, tester: LabTester) -> None:
    """403 unless ``caller`` outranks the account behind ``tester``."""
    target = tester.user
    if (target.is_superuser or target.is_admin_user) and not caller.is_superuser:
        raise PermissionDenied(
            "Only a superuser may change or delete an admin's lab-tester profile."
        )


class UpdateLabTesterView(AdminApiView):
    """Update or delete a lab tester (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Update a lab tester",
        request=UpdateLabTesterSerializer,
        responses={200: LabTesterPayloadSerializer},
    )
    def patch(self, request, id: int):
        tester = get_object_or_404(
            LabTester.objects.select_related("user", "created_by"), id=id
        )
        _refuse_higher_role(request.user, tester)

        serializer = UpdateLabTesterSerializer(
            instance=tester, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = tester.user
        for field in ("name", "email", "phone_number"):
            if field in data:
                setattr(user, field, data[field])

        tester.save()
        user.save(
            skip_full_clean=True,
            update_fields=["name", "email", "phone_number", "updated_at"],
        )

        return Response(lab_tester_payload(tester, include_totp=True))

    @extend_schema(
        summary="Delete a lab tester",
        responses={204: None},
    )
    def delete(self, request, id: int):
        tester = get_object_or_404(
            LabTester.objects.select_related("user", "created_by"), id=id
        )
        _refuse_higher_role(request.user, tester)
        # ``mark_deleted`` (not ``delete(deleted_by=...)``) for the same reason
        # as sales people; ``LabTester.guard_soft_delete`` still revokes the
        # user's sessions and tokens.
        with transaction.atomic():
            tester.mark_deleted(request.user)
            deactivate_if_roleless(tester.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
