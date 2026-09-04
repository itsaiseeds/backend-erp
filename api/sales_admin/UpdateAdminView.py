"""Admin update/delete endpoint: ``PATCH``/``DELETE`` ``/api/sales_admin/admins/<id>``.

Only a Django superuser may update or delete an application admin (enforced via
the ``IsSuperUser`` permission, mirroring ``AdminsView``). Extra ``pk`` kwargs
are rejected at the URL resolver, so a superuser can only mutate the admin
whose id is in the path. ``phone_number`` is validated for format and
uniqueness.

Soft-deleted admins are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import ExpiringTokenAuthentication, SessionAuthentication
from api.permissions import IsSuperUser
from authentication.models import Admin
from authentication.UserOperations import (
    AdminPayloadSerializer,
    UpdateAdminSerializer,
    admin_payload,
)


class UpdateAdminView(APIView):
    """Update or delete a single application admin (superuser only)."""

    # Refer to api/sales_admin/VerifyOTPView.py for how a view declares its own
    # authentication / permission classes instead of the global defaults.
    authentication_classes: list[type] = [ExpiringTokenAuthentication, SessionAuthentication]
    permission_classes: list[type] = [IsAuthenticated, IsSuperUser]

    @extend_schema(
        summary="Update an application admin",
        request=UpdateAdminSerializer,
        responses={200: AdminPayloadSerializer},
    )
    def patch(self, request, pk: int):
        admin = get_object_or_404(Admin.objects.select_related("user", "created_by"), pk=pk)

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
    def delete(self, request, pk: int):
        admin = get_object_or_404(
            Admin.objects.select_related("user", "created_by"), pk=pk
        )
        admin.delete(deleted_by=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
