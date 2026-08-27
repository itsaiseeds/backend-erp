"""Verify-an-OTP endpoint used by the sales admin website.

Validates a previously-generated OTP and issues credentials for the matching
user so their session is authenticated.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import MobileVerification

User = get_user_model()


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=10)
    otp = serializers.CharField(max_length=8)


class VerifyOTPView(APIView):
    """Validate an OTP, then (re)issue credentials for that user."""

    serializer_class = VerifyOTPSerializer

    # Pre-auth endpoint: allows an unauthenticated user to exchange an OTP
    # for credentials, so it opts out of the global auth defaults.
    authentication_classes: list[type] = []
    permission_classes: list[type] = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.filter(phone_number=data["phone_number"]).first()
        challenge = (
            MobileVerification.objects.filter(
                phone_number=data["phone_number"], is_used=False
            )
            .order_by("-created_at")
            .first()
        )
        if user is None or challenge is None or challenge.otp != data["otp"]:
            return Response({"detail": "Invalid phone number or OTP."}, status=400)
        if challenge.is_expired:
            return Response({"detail": "OTP has expired."}, status=400)

        challenge.mark_used()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "phone_number": user.phone_number,
                    "role": user.role,
                },
            }
        )
