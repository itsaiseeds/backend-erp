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
#   bash scripts/run.sh test-integration tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_returns_token
#
# The same pytest node strings work ad hoc inside the container:
#   docker compose exec -T web python -m pytest tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_returns_token -v

from __future__ import annotations

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
