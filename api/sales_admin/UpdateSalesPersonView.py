"""Sales person update/delete endpoint: ``PATCH``/``DELETE`` ``/api/sales-admin/sales-people/<id>``.

Only an application Admin may update or delete a sales person
(``admin_required`` on ``AdminApiView``, mirroring ``SalesPeopleView``). A
sales person cannot update itself or others. A bare Django superuser does
**not** hold an ``Admin`` profile (``is_admin_user`` requires an
``admin_profile`` row -- see ``authentication.models.User.is_admin_user``),
so a bare superuser is refused here; give the superuser an ``Admin`` profile
if they should be able to hire/fire sales people. ``phone_number`` is
validated for format and uniqueness.

Every admin also holds a fallback ``SalesPerson`` profile, so a sales person
may belong to an admin or a superuser. Only a superuser may touch those (403
otherwise): managing admins is superuser-only (``UpdateAdminView``), and this
endpoint writes the login phone number.

Soft-deleted sales people are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import SalesPerson, User
from authentication.UserOperations import (
    SalesPersonPayloadSerializer,
    UpdateSalesPersonSerializer,
    salesperson_payload,
)


def _refuse_higher_role(caller: User, salesperson: SalesPerson) -> None:
    """403 unless ``caller`` outranks the account behind ``salesperson``."""
    target = salesperson.user
    if (target.is_superuser or target.is_admin_user) and not caller.is_superuser:
        raise PermissionDenied(
            "Only a superuser may change or delete an admin's sales-person profile."
        )


class UpdateSalesPersonView(AdminApiView):
    """Update or delete a sales person (app admin only; superusers count as admins)."""

    admin_required = True

    @extend_schema(
        summary="Update a sales person",
        request=UpdateSalesPersonSerializer,
        responses={200: SalesPersonPayloadSerializer},
    )
    def patch(self, request, id: int):
        salesperson = get_object_or_404(
            SalesPerson.objects.select_related("user", "city", "created_by"), id=id
        )
        _refuse_higher_role(request.user, salesperson)

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
    def delete(self, request, id: int):
        salesperson = get_object_or_404(
            SalesPerson.objects.select_related("user", "city", "created_by"), id=id
        )
        _refuse_higher_role(request.user, salesperson)
        # ``mark_deleted`` rather than ``delete(deleted_by=...)``: the latter
        # gates on Django auth's ``authentication.delete_salesperson``
        # permission, which application admins do not hold. The API-level
        # ``admin_required`` gate above is the intended access control. Both
        # run ``SalesPerson.guard_soft_delete``, which revokes the user's
        # sessions and tokens.
        salesperson.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
