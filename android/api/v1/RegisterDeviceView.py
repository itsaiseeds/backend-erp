"""Device registration endpoint: ``POST /android/api/v1/devices/register``.

The app calls this after every login and whenever Firebase rotates its token, so
the server always knows which FCM token reaches the caller. Idempotent: sending
the same token again just refreshes it, and a token that was registered under a
different user (a shared phone) moves to the caller. Logging out forgets the
caller's devices (see ``LogoutView``).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.NotificationOperations import register_device
from android.api.base import AndroidSharedView


class RegisterDeviceSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(max_length=512)
    app_version = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")


class RegisterDeviceView(AndroidSharedView):
    """Register (or refresh) the caller's FCM token."""

    serializer_class = RegisterDeviceSerializer

    @extend_schema(
        summary="Register this device for push notifications",
        request=RegisterDeviceSerializer,
        responses={204: {"description": "Device registered."}},
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        register_device(
            request.user.pk,
            serializer.validated_data["fcm_token"],
            serializer.validated_data["app_version"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
