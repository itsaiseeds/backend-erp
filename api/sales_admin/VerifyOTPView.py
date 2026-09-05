"""TOTP login endpoint used by the sales admin website.

Verifies a 6-digit authenticator-app code against the user's enrolled TOTP
secret and opens a browser session for the matching user (replaces the old
SMS/email OTP flow). Session-only: never mints a bearer token (see
``android.api.v1.LoginView`` for the Android counterpart, which mints a token
and never opens a session).

**Brute-force protection.** A 6-digit code is trivially guessable without
throttling, so the endpoint runs three defenses together:

* Per-IP throttle (``VerifyOTPThrottle``): a single origin cannot burn
  through everyone's per-account lockout budget cheaply.
* Per-user lockout: after ``TOTP_MAX_ATTEMPTS`` (5) consecutive wrong codes
  the account is frozen for ``TOTP_LOCKOUT_MINUTES`` (5); during the window
  the endpoint responds with the same generic ``400`` as a wrong code so
  the caller cannot tell "I am locked" from "code was wrong" — that
  distinction would leak account existence.
* Replay refusal: ``User.verify_totp`` remembers the counter of every
  accepted code and refuses to accept the same counter twice.

The whole flow runs inside a ``transaction.atomic`` block with a
``select_for_update`` on the user row, so concurrent requests for the same
account cannot race the replay slot or the failure counter.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
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
    """User payload returned after a successful TOTP exchange.

    The session cookie itself is set via ``Set-Cookie`` (see ``login()``
    below), not returned in the body.
    """

    user = VerifyOTPUserSerializer()
    can_create_admin = serializers.BooleanField()
    can_create_sales_person = serializers.BooleanField()


class VerifyOTPThrottle(AnonRateThrottle):
    """Per-IP throttle for the pre-auth TOTP endpoint.

    The rate lives in ``settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']``
    under ``verify_otp``. Purpose: stop a single origin from cheaply burning
    through every admin's per-user lockout budget.
    """

    scope = "verify_otp"


# Same generic body for every failure mode so a caller cannot tell "unknown
# phone" from "wrong code" from "you are locked out" — all three collapse to
# the same 400 response and reveal no account-existence signal.
_GENERIC_FAILURE = {"detail": "Invalid phone number or TOTP code."}


class VerifyOTPView(APIView):
    """Validate a TOTP code, then (re)open a session for that user."""

    serializer_class = VerifyOTPSerializer

    # Pre-auth endpoint: lets an unauthenticated user exchange a TOTP code
    # for a session, so it opts out of the global auth defaults.
    authentication_classes: list[type] = []
    permission_classes: list[type] = [AllowAny]
    throttle_classes: list[type] = [VerifyOTPThrottle]

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={
            200: VerifyOTPResponseSerializer,
            400: {"description": "Invalid phone number or TOTP code."},
            429: {"description": "Too many requests from this IP; retry later."},
        },
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Serialize the whole login attempt for this user on the DB so two
        # concurrent requests can't both spend the "same code, once only"
        # replay slot, nor race the failed-attempt counter into an under-count.
        # ``select_for_update`` requires an open transaction.
        with transaction.atomic():
            user = (
                User.objects.select_for_update().filter(phone_number=data["phone_number"]).first()
            )
            if user is None or (not user.is_admin_user and not user.is_superuser):
                return Response(_GENERIC_FAILURE, status=400)

            # Return the same generic 400 whether the caller is locked or
            # simply wrong: distinguishing them (e.g. via 429) tells an
            # attacker "yes, this phone belongs to an admin".
            if user.is_totp_locked():
                return Response(_GENERIC_FAILURE, status=400)

            if not user.totp_enabled or not user.verify_totp(data["otp"]):
                user.register_failed_totp()
                return Response(_GENERIC_FAILURE, status=400)

            user.reset_totp_failures()
        # Open a browser session for the Flutter admin site. This rotates the
        # session key and returns a sessionid cookie.
        login(request, user)
        # Session ("cookie") auth enforces CSRF on non-GET requests, so make
        # sure the response carries a csrftoken cookie the SPA can echo back
        # with X-CSRFToken on later POSTs.
        get_token(request)
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
