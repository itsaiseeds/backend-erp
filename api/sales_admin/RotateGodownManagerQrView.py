"""Godown manager QR rotation: ``POST /api/sales-admin/godown-managers/<id>/rotate-qr``.

Only an application Admin may rotate (``admin_required``); a godown manager that
belongs to an admin or a superuser is superuser-only, like the update endpoint.
The old authenticator entry stops working at once and the new provisioning URI
is returned so the QR can be rendered. Soft-deleted godown managers are 404.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import GodownManager
from authentication.UserOperations import (
    GodownManagerPayloadSerializer,
    godown_manager_payload,
    rotate_totp_secret,
)

from .UpdateGodownManagerView import _refuse_higher_role


class RotateGodownManagerQrView(AdminApiView):
    """Rotate a godown manager's authenticator QR (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Rotate a godown manager's authenticator QR",
        request=None,
        responses={200: GodownManagerPayloadSerializer},
    )
    def post(self, request, id: int):
        manager = get_object_or_404(
            GodownManager.objects.select_related("user", "created_by"), id=id
        )
        _refuse_higher_role(request.user, manager)

        with transaction.atomic():
            rotate_totp_secret(manager.user)

        return Response(godown_manager_payload(manager, include_totp=True))
