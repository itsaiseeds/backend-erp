"""Reauthenticate endpoint: does the caller's credential still work?

Clients (Flutter admin site via session cookie, Android app via bearer token)
call ``GET /api/utilities/reauthenticate`` on startup / resume to check
whether their stored credential is still valid without having to make a real
business request first.

Behaviour
---------
* Valid credential -> ``200`` with the current user payload.
* Missing / expired / revoked credential -> ``401`` (surfaced by DRF from the
  configured authenticators; ``ExpiringTokenAuthentication`` additionally
  deletes an expired token as a side effect).

The view accepts either authentication scheme so the same URL serves both
clients.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import ExpiringTokenAuthentication, SessionAuthentication


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


class ReauthenticateView(APIView):
    """Confirm the caller's session cookie or bearer token is still valid."""

    authentication_classes: list[type] = [
        SessionAuthentication,
        ExpiringTokenAuthentication,
    ]
    permission_classes: list[type] = [IsAuthenticated]

    @extend_schema(
        summary="Check whether the caller's credential is still valid",
        responses={
            200: ReauthenticateResponseSerializer,
            401: {"description": "Missing, expired, or revoked credential."},
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
