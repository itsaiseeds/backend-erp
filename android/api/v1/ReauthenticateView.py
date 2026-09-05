"""Reauthenticate endpoint: does the caller's bearer token still work?

The Android counterpart of ``api.utilities.ReauthenticateView`` (which serves
the web's session cookie). The sales-person app calls
``GET /android/api/v1/auth/reauthenticate`` on startup / resume to check
whether its stored token is still valid without having to make a real
business request first. Token-only: never touches sessions.

Behaviour
---------
* Valid token -> ``200`` with the current user payload.
* Missing / expired / revoked token -> ``401`` (``ExpiringTokenAuthentication``
  additionally deletes an expired token as a side effect).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from android.api.base import AndroidBaseView


class AndroidReauthenticateUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    role = serializers.CharField()


class AndroidReauthenticateResponseSerializer(serializers.Serializer):
    user = AndroidReauthenticateUserSerializer()


class ReauthenticateView(AndroidBaseView):
    """Confirm the caller's bearer token is still valid."""

    @extend_schema(
        summary="Check whether the caller's bearer token is still valid",
        responses={
            200: AndroidReauthenticateResponseSerializer,
            401: {"description": "Missing, expired, or revoked token."},
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
            }
        )
