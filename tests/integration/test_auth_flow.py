"""Endpoint integration tests for the sales_admin TOTP (authenticator) auth flow.

These hit the live Django server over HTTP via the class-based helpers in
:mod:`tests.integration.base`. The ``django_test`` database is seeded by
sql/dml.sql with a superuser whose phone number is 9999999999; tests set up the
TOTP state for that user directly through the ORM before exercising the
endpoints.
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

import pytest

from tests.integration.base import IntegrationTestCase

pytestmark = pytest.mark.integration

SUPERUSER_PHONE = "9999999999"
TEST_TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # a valid base32 base32 secret


def _enroll_superuser():
    """Set the seeded superuser's TOTP secret and activate it via the ORM."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.get(phone_number=SUPERUSER_PHONE)
    user.totp_secret = TEST_TOTP_SECRET
    user.totp_enabled = True
    user.save(update_fields=["totp_secret", "totp_enabled"])
    return user


def _current_code() -> str:
    import pyotp

    return pyotp.TOTP(TEST_TOTP_SECRET).now()


class AuthFlowTest(IntegrationTestCase):
    """Covers the TOTP login + wrong-code behaviour of the sales admin API.
    tests/integration/test_auth_flow.py::AuthFlowTest
    """

    def test_totp_verify_returns_token(self):
        """tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_returns_token"""
        _enroll_superuser()
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
        _enroll_superuser()
        response = self.post(
            "/api/sales_admin/auth/otp/verify",
            json={"phone_number": SUPERUSER_PHONE, "otp": "000000"},
        )
        assert response.status_code == 400

    def test_totp_verify_requires_enrollment(self):
        """tests/integration/test_auth_flow.py::AuthFlowTest::test_totp_verify_requires_enrollment"""
        # User starts un-enrolled (totp_secret NULL, totp_enabled False).
        response = self.post(
            "/api/sales_admin/auth/otp/verify",
            json={"phone_number": SUPERUSER_PHONE, "otp": _current_code()},
        )
        assert response.status_code == 400
