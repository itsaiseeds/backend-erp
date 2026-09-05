"""TOTP login endpoint used by the sales-person Android app.

Verifies a 6-digit authenticator-app code against the user's enrolled TOTP
secret and issues a bearer token for the matching sales person -- the token
counterpart of ``api.sales_admin.VerifyOTPView`` (which issues a session
cookie for the web). This view never touches sessions: no ``login()``, no
``request.session``.

**Assumption:** sales-persons authenticate with the same TOTP scheme as
admins/superusers. If the real mobile credential differs (SMS OTP, password,
...), only the credential check in ``post`` below needs to change.

**Brute-force protection** mirrors ``VerifyOTPView``: a per-IP throttle, a
per-user lockout after ``TOTP_MAX_ATTEMPTS`` consecutive wrong codes, and TOTP
counter replay refusal, all behind the same generic 400 body so a caller
cannot distinguish "unknown phone" from "wrong code" from "locked out".
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=10)
    otp = serializers.CharField(max_length=8)


class LoginUserSerializer(serializers.Serializer):
    """The authenticated sales person, as returned by the login flow."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    role = serializers.CharField()


class LoginResponseSerializer(serializers.Serializer):
    """Credentials returned after a successful TOTP exchange."""

    token = serializers.CharField()
    user = LoginUserSerializer()


class LoginThrottle(AnonRateThrottle):
    """Per-IP throttle for the pre-auth Android login endpoint.

    The rate lives in ``settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']``
    under ``android_login``. Purpose: stop a single origin from cheaply
    burning through every sales person's per-account lockout budget.
    """

    scope = "android_login"


# Same generic body for every failure mode so a caller cannot tell "unknown
# phone" from "wrong code" from "you are locked out" -- all three collapse to
# the same 400 response and reveal no account-existence signal.
_GENERIC_FAILURE = {"detail": "Invalid phone number or TOTP code."}


class LoginView(APIView):
    """Validate a TOTP code, then issue a bearer token for that sales person."""

    serializer_class = LoginSerializer

    # Pre-auth endpoint: lets an unauthenticated user exchange a TOTP code for
    # a token, so it opts out of the global auth defaults.
    authentication_classes: list[type] = []
    permission_classes: list[type] = [AllowAny]
    throttle_classes: list[type] = [LoginThrottle]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: {"description": "Invalid phone number or TOTP code."},
            429: {"description": "Too many requests from this IP; retry later."},
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Serialize the whole login attempt for this user on the DB so two
        # concurrent requests can't both spend the "same code, once only"
        # replay slot, nor race the failed-attempt counter into an under-count.
        with transaction.atomic():
            user = (
                User.objects.select_for_update().filter(phone_number=data["phone_number"]).first()
            )
            if user is None or not user.is_salesperson:
                return Response(_GENERIC_FAILURE, status=400)

            if user.is_totp_locked():
                return Response(_GENERIC_FAILURE, status=400)

            if not user.totp_enabled or not user.verify_totp(data["otp"]):
                user.register_failed_totp()
                return Response(_GENERIC_FAILURE, status=400)

            user.reset_totp_failures()
            # Rotate the bearer token on every successful login so a
            # previously leaked key is invalidated by a fresh sign-in instead
            # of surviving for the whole TTL window.
            Token.objects.filter(user=user).delete()
            token = Token.objects.create(user=user)

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
