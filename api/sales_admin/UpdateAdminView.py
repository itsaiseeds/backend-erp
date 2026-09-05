"""Admin update/delete endpoint: ``PATCH``/``DELETE`` ``/api/sales_admin/admins/<id>``.

Only a Django superuser may update or delete an application admin
(``superuser_required`` on ``AdminApiView``, mirroring ``AdminsView``). Extra
``id`` kwargs are rejected at the URL resolver, so a superuser can only mutate
the admin whose id is in the path. ``phone_number`` is validated for format and
uniqueness.

Soft-deleted admins are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import Admin
from authentication.UserOperations import (
    AdminPayloadSerializer,
    UpdateAdminSerializer,
    admin_payload,
)


class UpdateAdminView(AdminApiView):
    """Update or delete a single application admin (superuser only)."""

    superuser_required = True

    @extend_schema(
        summary="Update an application admin",
        request=UpdateAdminSerializer,
        responses={200: AdminPayloadSerializer},
    )
    def patch(self, request, id: int):
        admin = get_object_or_404(
            Admin.objects.select_related("user", "created_by"), id=id
        )

        serializer = UpdateAdminSerializer(instance=admin, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = admin.user
        for field in ("name", "email", "phone_number"):
            if field in data:
                setattr(user, field, data[field])
        if "can_update_stock_count" in data:
            admin.can_update_stock_count = data["can_update_stock_count"]

        admin.save()
        user.save(
            skip_full_clean=True,
            update_fields=["name", "email", "phone_number", "updated_at"],
        )

        return Response(admin_payload(admin, include_totp=True))

    @extend_schema(
        summary="Delete an application admin",
        responses={204: None},
    )
    def delete(self, request, id: int):
        admin = get_object_or_404(
            Admin.objects.select_related("user", "created_by"), id=id
        )
        admin.delete(deleted_by=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
