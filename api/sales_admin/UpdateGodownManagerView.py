"""Godown manager update/delete: ``PATCH``/``DELETE`` ``/api/sales-admin/godown-managers/<id>``.

Only an application Admin may update or delete a godown manager
(``admin_required`` on ``AdminApiView``, mirroring ``GodownManagersView``). As
with sales people, a godown manager that belongs to an admin or a superuser may
only be touched by a superuser (403 otherwise): this endpoint writes the login
phone number.

Soft-deleted godown managers are never found (404).
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import GodownManager, User
from authentication.UserOperations import (
    GodownManagerPayloadSerializer,
    UpdateGodownManagerSerializer,
    deactivate_if_roleless,
    godown_manager_payload,
)


def _refuse_higher_role(caller: User, manager: GodownManager) -> None:
    """403 unless ``caller`` outranks the account behind ``manager``."""
    target = manager.user
    if (target.is_superuser or target.is_admin_user) and not caller.is_superuser:
        raise PermissionDenied(
            "Only a superuser may change or delete an admin's godown-manager profile."
        )


class UpdateGodownManagerView(AdminApiView):
    """Update or delete a godown manager (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Update a godown manager",
        request=UpdateGodownManagerSerializer,
        responses={200: GodownManagerPayloadSerializer},
    )
    def patch(self, request, id: int):
        manager = get_object_or_404(
            GodownManager.objects.select_related("user", "created_by"), id=id
        )
        _refuse_higher_role(request.user, manager)

        serializer = UpdateGodownManagerSerializer(
            instance=manager, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = manager.user
        for field in ("name", "email", "phone_number"):
            if field in data:
                setattr(user, field, data[field])

        manager.save()
        user.save(
            skip_full_clean=True,
            update_fields=["name", "email", "phone_number", "updated_at"],
        )

        return Response(godown_manager_payload(manager, include_totp=True))

    @extend_schema(
        summary="Delete a godown manager",
        responses={204: None},
    )
    def delete(self, request, id: int):
        manager = get_object_or_404(
            GodownManager.objects.select_related("user", "created_by"), id=id
        )
        _refuse_higher_role(request.user, manager)
        # ``mark_deleted`` (not ``delete(deleted_by=...)``) for the same reason
        # as sales people; ``GodownManager.guard_soft_delete`` still revokes the
        # user's sessions and tokens.
        with transaction.atomic():
            manager.mark_deleted(request.user)
            deactivate_if_roleless(manager.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
