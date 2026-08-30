"""Endpoint integration tests for the sales_admin TOTP (authenticator) login.

These hit the live Django server over HTTP via the class-based helpers in
:mod:`tests.integration.base`. The ``django_test`` database is seeded by
sql/dml.sql with:

* a TOTP-enabled superuser (phone 9999999999) whose secret is
  ``JBSWY3DPEHPK3PXP``, and
* a second user (phone 8888888888) with NO TOTP secret set.

Tests therefore compute codes directly with pyotp against the known seed
secret — there is no ORM access in these integration tests.
"""

# How to run (from the project root). All of these run INSIDE the web
# container, so the host Python never needs Django:
#   bash scripts/run.sh test-integration
#   bash scripts/run.sh test-integration tests/integration/test_auth_flow.py::AuthFlowTest
#   bash scripts/run.sh test-integration \
#     tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_returns_token
#
# The same pytest node strings work ad hoc inside the container:
#   docker compose exec -T web python -m pytest \
#     tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_returns_token -v

from __future__ import annotations

import os

import psycopg
import pyotp
import pytest

from tests.integration.base import IntegrationTestCase

pytestmark = pytest.mark.integration

SUPERUSER_PHONE = "9999999999"
SUPERUSER_TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # matches the sql/dml.sql seed
UNENROLLED_PHONE = "8888888888"


def _current_code() -> str:
    return pyotp.TOTP(SUPERUSER_TOTP_SECRET).now()


class AuthFlowTest(IntegrationTestCase):
    """Covers the TOTP login + wrong-code behaviour of the sales admin API.
    tests/integration/test_auth_flow.py::AuthFlowTest
    """

    def test_totp_verify_returns_token(self):
        """tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_returns_token"""
        response = self.post(
            "/api/sales_admin/auth/otp/verify",
            json={"phone_number": SUPERUSER_PHONE, "otp": _current_code()},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["token"]
        assert payload["user"]["phone_number"] == SUPERUSER_PHONE

    def test_totp_verify_wrong_code(self):
        """tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_wrong_code"""
        response = self.post(
            "/api/sales_admin/auth/otp/verify",
            json={"phone_number": SUPERUSER_PHONE, "otp": "000000"},
        )
        assert response.status_code == 400

    def test_totp_verify_requires_enrollment(self):
        """tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_requires_enrollment"""
        # User 8888888888 exists but has no TOTP secret enabled.
        response = self.post(
            "/api/sales_admin/auth/otp/verify",
            json={"phone_number": UNENROLLED_PHONE, "otp": _current_code()},
        )
        assert response.status_code == 400


def _test_db_connection():
    """Open a psycopg connection to the integration-test database.

    Mirrors IntegrationDbContext: real Postgres, credentials from the same env
    vars (TEST_DB_HOST / POSTGRES_*). Used to backdate rows the 24h-clock tests
    rely on, since these tests deliberately avoid ORM access.
    """
    return psycopg.connect(
        host=os.environ.get("TEST_DB_HOST", "db"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ.get("POSTGRES_USER", "django"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        dbname="django_test",
    )


class SessionAuthFlowTest(IntegrationTestCase):
    """Covers the 24h session + bearer-token credentials a successful login issues.
    tests/integration/test_auth_flow.py::SessionAuthFlowTest
    """

    def _login(self):
        return self.post(
            "/api/sales_admin/auth/otp/verify",
            json={"phone_number": SUPERUSER_PHONE, "otp": _current_code()},
        )

    def test_login_issues_24h_session_and_csrf_cookies(self):
        """tests/integration/test_auth_flow.py::SessionAuthFlowTest::test_login_issues_24h_session_and_csrf_cookies"""
        # Anonymous cannot read the superuser-only schema endpoint.
        assert self.get("/api/schema/").status_code == 401
        response = self._login()
        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "")
        assert "sessionid=" in set_cookie
        assert "Max-Age=86400" in set_cookie
        assert "csrftoken=" in set_cookie
        # The session cookie really authenticates: the same superuser-only
        # endpoint now answers 200, not the anonymous 401.
        assert self.get("/api/schema/").status_code == 200

    def test_expired_session_is_rejected(self):
        """tests/integration/test_auth_flow.py::SessionAuthFlowTest::test_expired_session_is_rejected"""
        assert self._login().status_code == 200
        with _test_db_connection() as conn:
            conn.execute(
                "UPDATE django_session SET expire_date = NOW() - INTERVAL '1 hour' "
                "WHERE expire_date > NOW()"
            )
        # An expired session falls back to anonymous: 401 again.
        assert self.get("/api/schema/").status_code == 401

    def test_verify_refreshes_token_clock_on_relogin(self):
        """tests/integration/test_auth_flow.py::SessionAuthFlowTest::test_verify_refreshes_token_clock_on_relogin"""
        first = self._login()
        assert first.status_code == 200
        token_key = first.json()["token"]
        with _test_db_connection() as conn:
            original_created = conn.execute(
                "SELECT created FROM authtoken_token WHERE key = %s", (token_key,)
            ).fetchone()[0]
            conn.execute(
                "UPDATE authtoken_token SET created = NOW() - INTERVAL '25 hours' "
                "WHERE key = %s",
                (token_key,),
            )
        second = self._login()
        assert second.status_code == 200
        assert second.json()["token"] == token_key
        with _test_db_connection() as conn:
            refreshed_created = conn.execute(
                "SELECT created FROM authtoken_token WHERE key = %s", (token_key,)
            ).fetchone()[0]
        assert refreshed_created > original_created
