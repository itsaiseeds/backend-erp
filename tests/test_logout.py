"""ORM-backed tests for ``POST /api/sales_admin/auth/logout``.

Logout must invalidate both credential paths (bearer token + browser
session), refuse anonymous callers, and be safe to call more than once.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from tests.common import DMLTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class LogoutTest(DMLTestCase):
    """Cover token invalidation, session flush, and permission gating.

    tests/test_logout.py::LogoutTest
    """

    URL = "/api/sales_admin/auth/logout"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

    def setUp(self):
        self.client = APIClient()

    # -- Permission gating ---------------------------------------------------

    def test_anonymous_gets_401(self):
        """tests/test_logout.py::LogoutTest::test_anonymous_gets_401"""
        self.assertEqual(self.client.post(self.URL).status_code, 401)

    # -- Bearer token --------------------------------------------------------

    def test_token_login_is_revoked(self):
        """The caller's Token row is deleted and reuse returns 401.

        tests/test_logout.py::LogoutTest::test_token_login_is_revoked
        """
        token = Token.objects.create(user=self.superuser)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(self.URL)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())

        # Re-using the same key is rejected.
        followup = self.client.get("/api/utilities/reauthenticate")
        self.assertEqual(followup.status_code, 401)

    # -- Session cookie ------------------------------------------------------

    def test_session_login_is_flushed(self):
        """The Django session is flushed; the cookie no longer authenticates.

        tests/test_logout.py::LogoutTest::test_session_login_is_flushed
        """
        self.client.force_login(self.superuser)
        # Sanity: session-authenticated requests work before logout.
        self.assertEqual(self.client.get("/api/utilities/reauthenticate").status_code, 200)

        response = self.client.post(self.URL)
        self.assertEqual(response.status_code, 204)

        self.assertEqual(self.client.get("/api/utilities/reauthenticate").status_code, 401)

    # -- Idempotency ---------------------------------------------------------

    def test_logout_without_prior_token_is_204(self):
        """A user with no bearer token but a session can still log out cleanly.

        tests/test_logout.py::LogoutTest::test_logout_without_prior_token_is_204
        """
        self.client.force_login(self.superuser)
        self.assertFalse(Token.objects.filter(user=self.superuser).exists())

        self.assertEqual(self.client.post(self.URL).status_code, 204)
