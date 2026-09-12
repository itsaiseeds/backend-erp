"""ORM-backed session lifecycle tests for the sales-admin website.

The whole cookie lifecycle -- TOTP login, what the session identifies, expiry,
and logout -- shares one fixture and one ``dml.sql`` load, so it lives in one
class. See ``tests/android/test_login.py`` and
``tests/android/test_authenticated_endpoints.py`` for the Android app's
bearer-token counterparts; the web side here never touches tokens.

That a bearer token does *not* authenticate these endpoints, and that anonymous
callers get 401, is pinned once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.authtoken.models import Token

from authentication.models import User
from tests.common import WebApiTestCase

REAUTHENTICATE_URL = "/api/utilities/reauthenticate"
LOGOUT_URL = "/api/sales-admin/auth/logout"


class SessionAuthFlowTest(WebApiTestCase):
    """Cover the session behavior after successful TOTP login.

    tests/test_auth_flow.py::SessionAuthFlowTest
    """

    @classmethod
    def setUpTestData(cls):
        """Use the DML-seeded superuser for all login-flow tests in this class."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")

    def _login(self):
        return self.client.post(
            "/api/sales-admin/auth/otp/verify",
            {
                "phone_number": self.superuser.phone_number,
                "otp": self.superuser.totp.now(),
            },
            format="json",
        )

    def test_login_issues_24h_session_and_csrf_cookies(self):
        """tests/test_auth_flow.py::SessionAuthFlowTest::test_login_issues_24h_session_and_csrf_cookies"""
        self.assertEqual(self.client.get("/api/schema/").status_code, 401)

        response = self._login()

        self.assertEqual(response.status_code, 200)
        self.assertIn("sessionid", response.cookies)
        self.assertEqual(response.cookies["sessionid"]["max-age"], 86400)
        self.assertIn("csrftoken", response.cookies)
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)

    def test_expired_session_is_rejected(self):
        """tests/test_auth_flow.py::SessionAuthFlowTest::test_expired_session_is_rejected"""
        self.assertEqual(self._login().status_code, 200)
        Session.objects.filter(expire_date__gt=timezone.now()).update(
            expire_date=timezone.now() - timedelta(hours=1)
        )

        self.assertEqual(self.client.get("/api/schema/").status_code, 401)

    def test_verify_does_not_issue_a_token(self):
        """Web login never touches ``authtoken_token`` -- session cookie only.

        tests/test_auth_flow.py::SessionAuthFlowTest::test_verify_does_not_issue_a_token
        """
        response = self._login()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn("token", response.data)
        self.assertFalse(Token.objects.filter(user=self.superuser).exists())

    def test_session_expiry_is_fixed_from_creation_not_sliding(self):
        """The 24h window is set once at login and never extended by activity.

        ``SESSION_SAVE_EVERY_REQUEST`` is not set (defaults to ``False``), so
        Django only re-saves -- and thus only re-stamps ``expire_date`` -- when
        session *data* changes, not merely when it is read. A later
        authenticated request must therefore leave ``expire_date`` untouched.

        tests/test_auth_flow.py::SessionAuthFlowTest::test_session_expiry_is_fixed_from_creation_not_sliding
        """
        self.assertEqual(self._login().status_code, 200)
        session = Session.objects.get()
        expire_date_at_login = session.expire_date

        # An authenticated request some time later must not push the expiry out.
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.expire_date, expire_date_at_login)

    # -- what the session identifies -----------------------------------------

    def test_reauthenticate_describes_the_logged_in_user(self):
        """The Flutter admin site calls this on startup / resume.

        tests/test_auth_flow.py::SessionAuthFlowTest::test_reauthenticate_describes_the_logged_in_user
        """
        self.login_as(self.superuser)

        response = self.client.get(REAUTHENTICATE_URL)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["user"]["id"], self.superuser.id)
        self.assertEqual(response.data["user"]["phone_number"], self.superuser.phone_number)
        self.assertEqual(response.data["user"]["role"], "superuser")
        self.assertTrue(response.data["can_create_admin"])
        self.assertTrue(response.data["can_create_sales_person"])

    # -- logout ---------------------------------------------------------------

    def test_logout_flushes_the_session_and_is_safe_to_repeat(self):
        """The cookie stops authenticating, and a second logout is still a 204.

        tests/test_auth_flow.py::SessionAuthFlowTest::test_logout_flushes_the_session_and_is_safe_to_repeat
        """
        self.login_as(self.superuser)
        # Sanity: session-authenticated requests work before logout.
        self.assertEqual(self.client.get(REAUTHENTICATE_URL).status_code, 200)

        self.assertEqual(self.client.post(LOGOUT_URL).status_code, 204)
        self.assertEqual(self.client.get(REAUTHENTICATE_URL).status_code, 401)

        # Logging in again and logging straight back out, with no request in
        # between, must also succeed.
        self.login_as(self.superuser)
        self.assertEqual(self.client.post(LOGOUT_URL).status_code, 204)
