"""Shared test-case base class for the Android app's token-only endpoints."""

from __future__ import annotations

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from tests.common import DMLTestCase


class AndroidApiTestCase(DMLTestCase):
    """Base for token-only Android endpoint tests.

    Provides an unauthenticated :class:`APIClient` per test and the one
    credential mechanism the Android side ever uses -- a bearer ``Token``
    header -- so individual test modules don't hand-roll their own
    ``_auth_as`` / ``_clear_auth`` helpers. See
    ``tests.common.WebApiTestCase`` for the session-based counterpart.
    """

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def login_as(self, user) -> Token:
        """Authenticate ``self.client`` as ``user`` via a bearer token.

        Returns the :class:`Token` so a test can inspect or mutate it (e.g.
        to age it past the TTL).
        """
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return token

    def clear_auth(self) -> None:
        """Drop the current bearer token, leaving the client anonymous."""
        self.client.credentials()
