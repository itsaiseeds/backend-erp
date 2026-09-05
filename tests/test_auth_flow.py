"""ORM-backed session lifecycle tests for sales-admin TOTP login.

See ``tests/android/test_login.py`` for the Android app's bearer-token
lifecycle counterpart -- the web login here never touches tokens.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.utils import timezone
from rest_framework.authtoken.models import Token

from authentication.models import User
from tests.common import WebApiTestCase


class SessionAuthFlowTest(WebApiTestCase):
    """Cover the session behavior after successful TOTP login.

    tests/test_auth_flow.py::SessionAuthFlowTest
    """

    @classmethod
    def setUpTestData(cls):
        """Use the DML-seeded superuser for all login-flow tests in this class."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")

    def setUp(self):
        super().setUp()
        cache.clear()  # reset the verify_otp per-IP throttle counter

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
