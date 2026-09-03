"""ORM-backed session and token lifecycle tests for sales-admin TOTP login."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from authentication.models import User
from tests.common import DMLTestCase


class SessionAuthFlowTest(DMLTestCase):
    """Cover the session and bearer-token behavior after successful TOTP login.

    tests/test_auth_flow.py::SessionAuthFlowTest
    """

    @classmethod
    def setUpTestData(cls):
        """Use the DML-seeded superuser for all login-flow tests in this class."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")

    def setUp(self):
        """Create an unauthenticated API client for every test in this class."""
        self.client = APIClient()
        cache.clear()  # reset the verify_otp per-IP throttle counter

    def _login(self):
        return self.client.post(
            "/api/sales_admin/auth/otp/verify",
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

    def test_verify_rotates_token_and_starts_fresh_clock(self):
        """A fresh login discards the old token and issues a new key.

        Also documents the replay-defence knock-on: within one 30s window
        the same OTP would be refused, so this test resets ``totp_last_counter``
        between logins to isolate rotation behaviour.

        tests/test_auth_flow.py::SessionAuthFlowTest::test_verify_rotates_token_and_starts_fresh_clock
        """
        first = self._login()
        self.assertEqual(first.status_code, 200, first.content)
        first_key = first.data["token"]
        # Age the token so we can prove the follow-up login re-created it
        # (a rotated token has a brand-new ``created`` at "now").
        Token.objects.filter(key=first_key).update(created=timezone.now() - timedelta(hours=25))
        # Un-burn the accepted counter so the same OTP can succeed again,
        # isolating "token rotation" from "replay defense".
        User.objects.filter(pk=self.superuser.pk).update(totp_last_counter=None)

        second = self._login()

        self.assertEqual(second.status_code, 200, second.content)
        self.assertNotEqual(second.data["token"], first_key)
        self.assertFalse(Token.objects.filter(key=first_key).exists())
        new_token = Token.objects.get(key=second.data["token"])
        self.assertGreater(new_token.created, timezone.now() - timedelta(minutes=1))
