"""Utility endpoint: sales admins to call, ``GET /android/api/v1/utilities/sales-admins``.

Lists only admins who opted in (``Admin.share_contact``) and exposes **name and
phone number only** -- no id, no email, nothing else off the user record. A
soft-deleted admin drops out (the default manager hides it). Token-only; open to
either Android role.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from android.api.base import AndroidSharedView
from authentication.models import Admin


class SalesAdminContactSerializer(serializers.Serializer):
    """Output shape for one shared admin contact (schema only)."""

    name = serializers.CharField()
    phone_number = serializers.CharField()


class SalesAdminsView(AndroidSharedView):
    """List the sales admins who share their contact."""

    @extend_schema(
        summary="List sales admins who share their contact (name and phone only)",
        responses={200: SalesAdminContactSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        admins = (
            Admin.objects.filter(share_contact=True)
            .select_related("user")
            .order_by("user__name", "id")
        )
        return Response(
            [
                {"name": admin.user.name, "phone_number": admin.user.phone_number}
                for admin in admins
            ]
        )
