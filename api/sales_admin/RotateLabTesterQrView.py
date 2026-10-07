"""Lab tester QR rotation: ``POST /api/sales-admin/lab-testers/<id>/rotate-qr``.

Only an application Admin may rotate (``admin_required``); a lab tester that
belongs to an admin or a superuser is superuser-only, like the update endpoint.
The old authenticator entry stops working at once and the new provisioning URI
is returned so the QR can be rendered. Soft-deleted lab testers are 404.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from api.admin import AdminApiView
from authentication.models import LabTester
from authentication.UserOperations import (
    LabTesterPayloadSerializer,
    lab_tester_payload,
    rotate_totp_secret,
)

from .UpdateLabTesterView import _refuse_higher_role


class RotateLabTesterQrView(AdminApiView):
    """Rotate a lab tester's authenticator QR (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Rotate a lab tester's authenticator QR",
        request=None,
        responses={200: LabTesterPayloadSerializer},
    )
    def post(self, request, id: int):
        tester = get_object_or_404(
            LabTester.objects.select_related("user", "created_by"), id=id
        )
        _refuse_higher_role(request.user, tester)

        with transaction.atomic():
            rotate_totp_secret(tester.user)

        return Response(lab_tester_payload(tester, include_totp=True))
