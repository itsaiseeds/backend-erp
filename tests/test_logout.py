"""ORM-backed tests for ``POST /api/sales_admin/auth/logout``.

Web logout is session-only: it must flush the browser session, refuse
anonymous callers, and be safe to call more than once. See
``tests/android/test_logout.py`` for the Android app's bearer-token
counterpart.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model

from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class LogoutTest(WebApiTestCase):
    """Cover session flush and permission gating.

    tests/test_logout.py::LogoutTest
    """

    URL = "/api/sales_admin/auth/logout"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

    # -- Permission gating ---------------------------------------------------

    def test_anonymous_gets_401(self):
        """tests/test_logout.py::LogoutTest::test_anonymous_gets_401"""
        self.assertEqual(self.client.post(self.URL).status_code, 401)

    # -- Session cookie ------------------------------------------------------

    def test_session_login_is_flushed(self):
        """The Django session is flushed; the cookie no longer authenticates.

        tests/test_logout.py::LogoutTest::test_session_login_is_flushed
        """
        self.login_as(self.superuser)
        # Sanity: session-authenticated requests work before logout.
        self.assertEqual(self.client.get("/api/utilities/reauthenticate").status_code, 200)

        response = self.client.post(self.URL)
        self.assertEqual(response.status_code, 204)

        self.assertEqual(self.client.get("/api/utilities/reauthenticate").status_code, 401)

    # -- Idempotency ---------------------------------------------------------

    def test_logout_without_prior_session_activity_is_204(self):
        """A freshly logged-in session can still log out cleanly.

        tests/test_logout.py::LogoutTest::test_logout_without_prior_session_activity_is_204
        """
        self.login_as(self.superuser)
        self.assertEqual(self.client.post(self.URL).status_code, 204)
