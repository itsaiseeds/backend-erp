"""ORM-backed tests for the shared ``/api/utilities/reauthenticate`` endpoint.

The endpoint answers the "is my token still valid?" question for both
clients, so it must accept the Android bearer token and the admin site's
session cookie, and it must return ``401`` when the credential is missing,
stale, or from a soft-deleted account.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from tests.common import DMLTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class ReauthenticateTest(DMLTestCase):
    """Verify the reauth endpoint's contract for every auth path.

    tests/test_reauthenticate.py::ReauthenticateTest
    """

    URL = "/api/utilities/reauthenticate"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

    def setUp(self):
        self.client = APIClient()

    # -- Unauthenticated -----------------------------------------------------

    def test_anonymous_gets_401(self):
        """tests/test_reauthenticate.py::ReauthenticateTest::test_anonymous_gets_401"""
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 401)

    # -- Bearer token --------------------------------------------------------

    def test_fresh_token_is_accepted(self):
        """tests/test_reauthenticate.py::ReauthenticateTest::test_fresh_token_is_accepted"""
        token = Token.objects.create(user=self.superuser)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["user"]["id"], self.superuser.id)
        self.assertEqual(response.data["user"]["phone_number"], SUPERUSER_PHONE)
        self.assertEqual(response.data["user"]["role"], "superuser")
        self.assertTrue(response.data["can_create_admin"])
        self.assertTrue(response.data["can_create_sales_person"])

    def test_expired_token_is_rejected_and_deleted(self):
        """tests/test_reauthenticate.py::ReauthenticateTest::test_expired_token_is_rejected_and_deleted"""
        token = Token.objects.create(user=self.superuser)
        # Age the token past the 24h TTL. ``ExpiringTokenAuthentication`` must
        # both reject and delete it.
        Token.objects.filter(key=token.key).update(created=timezone.now() - timedelta(hours=48))

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get(self.URL)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_unknown_token_is_rejected(self):
        """tests/test_reauthenticate.py::ReauthenticateTest::test_unknown_token_is_rejected"""
        self.client.credentials(HTTP_AUTHORIZATION="Token not-a-real-token")
        self.assertEqual(self.client.get(self.URL).status_code, 401)

    # -- Session cookie ------------------------------------------------------

    def test_session_login_is_accepted(self):
        """A logged-in browser session (used by the Flutter admin site) works.

        tests/test_reauthenticate.py::ReauthenticateTest::test_session_login_is_accepted
        """
        self.client.force_login(self.superuser)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["user"]["id"], self.superuser.id)
