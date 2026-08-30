"""TOTP login endpoint used by the sales admin website.

Verifies a 6-digit authenticator-app code against the user's enrolled TOTP
secret and issues credentials for the matching user so their session is
authenticated (replaces the old SMS/email OTP flow).

A successful login issues both credential forms:

* a browser **session cookie** (24h, see ``SESSION_COOKIE_AGE``), used by the
  Flutter admin website, and
* a **bearer token** (24h, see ``TOKEN_TTL_HOURS``), used by the mobile app;
  re-login on a fresh verification.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model, login
from django.middleware.csrf import get_token
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=10)
    otp = serializers.CharField(max_length=8)


class VerifyOTPUserSerializer(serializers.Serializer):
    """The authenticated user, as returned by the login flow."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    role = serializers.CharField()


class VerifyOTPResponseSerializer(serializers.Serializer):
    """Credentials returned after a successful TOTP exchange."""

    token = serializers.CharField()
    user = VerifyOTPUserSerializer()
    can_create_admin = serializers.BooleanField()
    can_create_sales_person = serializers.BooleanField()


class VerifyOTPView(APIView):
    """Validate a TOTP code, then (re)issue credentials for that user."""

    serializer_class = VerifyOTPSerializer

    # Pre-auth endpoint: lets an unauthenticated user exchange a TOTP code
    # for credentials, so it opts out of the global auth defaults.
    authentication_classes: list[type] = []
    permission_classes: list[type] = [AllowAny]

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={
            200: VerifyOTPResponseSerializer,
            400: {"description": "Invalid phone number or TOTP code."},
        },
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.filter(phone_number=data["phone_number"]).first()
        if user is None or not user.totp_enabled or not user.verify_totp(data["otp"]):
            return Response({"detail": "Invalid phone number or TOTP code."}, status=400)

        token, _ = Token.objects.get_or_create(user=user)
        # Fresh login => restart the token's 24h clock.
        token.created = timezone.now()
        token.save(update_fields=["created"])
        # Open a browser session for the Flutter admin site (same TOTP, one
        # flow). This rotates the session key and returns a sessionid cookie.
        login(request, user)
        # Session ("cookie") auth enforces CSRF on non-GET requests, so make
        # sure the response carries a csrftoken cookie the SPA can echo back
        # with X-CSRFToken on later POSTs.
        get_token(request)
        return Response(
            {
                "token": token.key,
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
