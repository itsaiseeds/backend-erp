"""Enroll a user in authenticator-app (TOTP) login for the sales admin website.

Two authenticated endpoints:

* ``POST /auth/totp/enroll``        - generate & store a fresh TOTP secret for a
  user, returning the provisioning URI, the base32 secret, and a QR code (PNG,
  base64-encoded) for the user to scan into their authenticator app.
* ``POST /auth/totp/verify-enroll`` - verify a code the user reads from their
  app; on success the secret is activated (``totp_enabled``) for login.

Enrollment is authenticated (session auth + Admin profile) so only authorised
users can set up/rotate a TOTP secret.
"""

from __future__ import annotations

import base64
import io

import qrcode
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response

from api.admin import AdminApiView

User = get_user_model()


class EnrollSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        source="user",
    )


class VerifyEnrollSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        source="user",
    )
    code = serializers.CharField(max_length=8)


def _qr_base64(data: str) -> str:
    """Render ``data`` as a QR code and return it base64-encoded (PNG)."""
    img = qrcode.make(data)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class TOTPEnrollView(AdminApiView):
    """Generate and activate a TOTP secret for a user."""

    def post(self, request, *args, **kwargs):
        serializer = EnrollSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user") or request.user

        secret = user.generate_totp_secret()
        user.save(update_fields=["totp_secret", "totp_enabled"])
        uri = user.totp_provisioning_uri()

        return Response(
            {
                "user_id": user.id,
                "phone_number": user.phone_number,
                "secret": secret,
                "provisioning_uri": uri,
                "qr_code_base64": _qr_base64(uri),
            }
        )


class VerifyTOTPEnrollView(AdminApiView):
    """Verify a code to activate the generated TOTP secret for a user."""

    def post(self, request, *args, **kwargs):
        serializer = VerifyEnrollSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = data.get("user") or request.user

        if not user.has_totp_secret:
            return Response(
                {"detail": "No pending TOTP secret to verify."}, status=400
            )
        if not user.verify_totp(data["code"]):
            return Response({"detail": "Invalid TOTP code."}, status=400)

        user.enable_totp()
        return Response({"detail": "TOTP enabled.", "user_id": user.id})
