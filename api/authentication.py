"""Authentication classes shared by the whole API.

Ships the expiring bearer-token scheme used by the mobile app: a token stops
working ``TOKEN_TTL_HOURS`` (default 24) after its last login.

Both classes advertise a ``WWW-Authenticate`` challenge: DRF 3.18+ coerces an
unauthenticated request from ``401`` down to ``403`` unless the first configured
authenticator provides a challenge header, and anonymous callers must get real
``401`` responses so clients (and tests) can distinguish "no credentials" from
"forbidden".
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import (
    SessionAuthentication as DRFSessionAuthentication,
)
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class SessionAuthentication(DRFSessionAuthentication):
    """Session-cookie auth (sales admin website) with a real challenge header.

    DRF uses the *first* configured authenticator's ``authenticate_header`` to
    decide whether a request may respond ``401`` instead of ``403``; the parent
    returns ``None``, which silently turns every anonymous request into a 403.
    Returning a header here keeps the correct ``401`` semantics.
    """

    def authenticate_header(self, request):
        return 'Session realm="api"'


class ExpiringTokenAuthentication(TokenAuthentication):
    """DRF bearer-token auth that rejects tokens older than ``TOKEN_TTL_HOURS``.

    The parent :class:`TokenAuthentication` only verifies the token exists and
    its user is active; this subclass additionally enforces a time-to-live so a
    stale or stolen token cannot be used forever. Expired tokens are deleted on
    first use, so the next request forces a fresh login.
    """

    def authenticate_credentials(self, key: str):
        user, token = super().authenticate_credentials(key)
        if token.created < timezone.now() - timedelta(hours=settings.TOKEN_TTL_HOURS):
            token.delete()
            raise AuthenticationFailed("Token has expired.")
        return user, token

    def authenticate_header(self, request):
        return 'Bearer realm="api"'
