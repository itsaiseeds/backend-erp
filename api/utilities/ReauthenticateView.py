"""Reauthenticate endpoint: does the caller's session still work?

The Flutter admin site calls ``GET /api/utilities/reauthenticate`` on startup
/ resume to check whether its session cookie is still valid without having to
make a real business request first. Session-only: never touches bearer tokens
(see ``android.api.v1.ReauthenticateView`` for the Android counterpart).

Behaviour
---------
* Valid session -> ``200`` with the current user payload.
* Missing / expired / revoked session -> ``401``.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from api.admin import AdminApiView


class ReauthenticateUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    role = serializers.CharField()


class ReauthenticateResponseSerializer(serializers.Serializer):
    """Mirrors the fields ``VerifyOTPView`` returns on a fresh login.

    The client uses the capability booleans to decide which admin-management
    UI to show; surfacing them here keeps a long-lived session in step with
    a role change (e.g. an admin who was demoted after their initial login).
    """

    user = ReauthenticateUserSerializer()
    can_create_admin = serializers.BooleanField()
    can_create_sales_person = serializers.BooleanField()


class ReauthenticateView(AdminApiView):
    """Confirm the caller's session cookie is still valid."""

    @extend_schema(
        summary="Check whether the caller's session is still valid",
        responses={
            200: ReauthenticateResponseSerializer,
            401: {"description": "Missing, expired, or revoked session."},
        },
    )
    def get(self, request):
        user = request.user
        return Response(
            {
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "phone_number": user.phone_number,
                    "role": user.role,
                },
                "can_create_admin": user.is_superuser,
                "can_create_sales_person": user.is_superuser or user.is_admin_user,
            }
        )
