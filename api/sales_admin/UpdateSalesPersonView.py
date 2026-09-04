"""Sales person update/delete endpoint: ``PATCH``/``DELETE`` ``/api/sales_admin/sales-people/<id>``.

Only an application Admin may update a sales person (enforced via the
``IsAdminUser`` permission, mirroring ``SalesPeopleView``). A sales person
cannot update itself or others and a superuser only manages admins, so only
an app admin can patch a sales person row. ``phone_number`` is validated for
format and uniqueness. A sales person may be deleted by an application Admin
or a Django superuser.

Soft-deleted sales people are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import ExpiringTokenAuthentication, SessionAuthentication
from api.permissions import IsAdminUser
from authentication.models import SalesPerson
from authentication.UserOperations import (
    SalesPersonPayloadSerializer,
    UpdateSalesPersonSerializer,
    salesperson_payload,
)


class UpdateSalesPersonView(APIView):
    """Update a sales person (app admin only) or delete one (admin or superuser)."""

    # Refer to api/sales_admin/VerifyOTPView.py for how a view declares its own
    # authentication / permission classes instead of the global defaults.
    authentication_classes: list[type] = [ExpiringTokenAuthentication, SessionAuthentication]
    permission_classes: list[type] = [IsAuthenticated, IsAdminUser]

    def get_permissions(self):
        # PATCH is app-admin only. A DELETE requires an authenticated actor who
        # is an app admin or a superuser (enforced in ``delete``).
        if self.request.method == "DELETE":
            return [IsAuthenticated()]
        return super().get_permissions()

    @extend_schema(
        summary="Update a sales person",
        request=UpdateSalesPersonSerializer,
        responses={200: SalesPersonPayloadSerializer},
    )
    def patch(self, request, pk: int):
        salesperson = get_object_or_404(
            SalesPerson.objects.select_related("user", "city", "created_by"), pk=pk
        )

        serializer = UpdateSalesPersonSerializer(
            instance=salesperson, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = salesperson.user
        for field in ("name", "email", "phone_number"):
            if field in data:
                setattr(user, field, data[field])
        if "city" in data:
            salesperson.city = data["city"]

        salesperson.save()
        user.save(
            skip_full_clean=True,
            update_fields=["name", "email", "phone_number", "updated_at"],
        )

        return Response(salesperson_payload(salesperson, include_totp=True))

    @extend_schema(
        summary="Delete a sales person",
        responses={204: None},
    )
    def delete(self, request, pk: int):
        # A sales person may be deleted by an app admin OR a superuser.
        actor = request.user
        if not actor.is_admin_user and not actor.is_superuser:
            raise PermissionDenied("Only an admin or superuser may delete a sales person.")

        salesperson = get_object_or_404(
            SalesPerson.objects.select_related("user", "city", "created_by"), pk=pk
        )
        salesperson.delete(deleted_by=actor)
        return Response(status=status.HTTP_204_NO_CONTENT)
