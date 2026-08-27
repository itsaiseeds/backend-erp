"""Request-an-OTP endpoint used by the sales admin website.

Creates a :class:`~authentication.models.MobileVerification` challenge for a
phone number. The user need not exist yet; the response is deliberately vague
so it does not reveal which numbers are registered.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import MobileVerification

User = get_user_model()


class GenerateOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=10)


class GenerateOTPView(APIView):
    """Create an OTP challenge for a phone number (pre-auth)."""

    serializer_class = GenerateOTPSerializer

    # Pre-auth endpoints cannot already be authenticated; opt out of the
    # global IsAuthenticated default and of session/token credential checks.
    authentication_classes: list[type] = []
    permission_classes: list[type] = [AllowAny]

    def post(self, request):
        serializer = GenerateOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        user = User.objects.filter(phone_number=phone_number).first()
        MobileVerification.objects.create(user=user, phone_number=phone_number)
        return Response({"phone_number": phone_number, "sent": True})
