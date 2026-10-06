"""Sales person QR rotation: ``POST /api/sales-admin/sales-people/<id>/rotate-qr``.

Only an application Admin may rotate (``admin_required``); a sales person that
belongs to an admin or a superuser is superuser-only, like the update endpoint.
The old authenticator entry stops working at once and the new provisioning URI
is returned so the QR can be rendered. Soft-deleted sales people are 404.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import SalesPerson
from authentication.UserOperations import (
    SalesPersonPayloadSerializer,
    rotate_totp_secret,
    salesperson_payload,
)

from .UpdateSalesPersonView import _refuse_higher_role


class RotateSalesPersonQrView(AdminApiView):
    """Rotate a sales person's authenticator QR (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Rotate a sales person's authenticator QR",
        request=None,
        responses={200: SalesPersonPayloadSerializer},
    )
    def post(self, request, id: int):
        salesperson = get_object_or_404(
            SalesPerson.objects.select_related("user", "city", "created_by"), id=id
        )
        _refuse_higher_role(request.user, salesperson)

        with transaction.atomic():
            rotate_totp_secret(salesperson.user)

        return Response(salesperson_payload(salesperson, include_totp=True))
