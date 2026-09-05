"""ORM-backed tests for the web session-only ``/api/utilities/reauthenticate``.

The Flutter admin site calls this on startup / resume to check whether its
session cookie is still valid. Session-only: see
``tests/android/test_reauthenticate.py`` for the Android bearer-token
counterpart.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class ReauthenticateTest(WebApiTestCase):
    """Verify the web reauth endpoint's contract.

    tests/test_reauthenticate.py::ReauthenticateTest
    """

    URL = "/api/utilities/reauthenticate"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

    def test_anonymous_gets_401(self):
        """tests/test_reauthenticate.py::ReauthenticateTest::test_anonymous_gets_401"""
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 401)

    def test_session_login_is_accepted(self):
        """A logged-in browser session (used by the Flutter admin site) works.

        tests/test_reauthenticate.py::ReauthenticateTest::test_session_login_is_accepted
        """
        self.login_as(self.superuser)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["user"]["id"], self.superuser.id)
        self.assertEqual(response.data["user"]["phone_number"], SUPERUSER_PHONE)
        self.assertEqual(response.data["user"]["role"], "superuser")
        self.assertTrue(response.data["can_create_admin"])
        self.assertTrue(response.data["can_create_sales_person"])

    def test_bearer_token_is_rejected(self):
        """A bearer token never authenticates the web endpoint (session-only).

        tests/test_reauthenticate.py::ReauthenticateTest::test_bearer_token_is_rejected
        """
        token = Token.objects.create(user=self.superuser)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(self.client.get(self.URL).status_code, 401)
