"""Authentication classes shared by the whole API.

Ships the expiring bearer-token scheme used by the mobile app: a token stops
working ``TOKEN_TTL_HOURS`` (default 24) after its last login.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


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
