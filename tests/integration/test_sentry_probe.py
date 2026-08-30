"""Integration test for the /api/test-sentry/ error-tracking probe.

Hits the live server: unauthenticated callers get 401; a logged-in superuser
(TOTP login, as seeded by sql/dml.sql) triggers the exception and gets 500.
The conftest autouse fixture resets the DB per test, so each case is isolated.
"""

from __future__ import annotations

import pyotp
import pytest

from tests.integration.base import IntegrationTestCase

pytestmark = pytest.mark.integration

SUPERUSER_PHONE = "9999999999"
SUPERUSER_TOTP_SECRET = "JBSWY3DPEHPK3PXP"  # matches the sql/dml.sql seed


class SentryProbeTest(IntegrationTestCase):
    """Covers access control + exception behaviour of the Sentry test endpoint.
    tests/integration/test_sentry_probe.py::SentryProbeTest
    """

    def test_unauthenticated_is_rejected(self):
        """tests/integration/test_sentry_probe.py::SentryProbeTest::test_unauthenticated_is_rejected"""
        response = self.get("/api/test-sentry/")
        assert response.status_code == 401

    def test_superuser_triggers_exception(self):
        """tests/integration/test_sentry_probe.py::SentryProbeTest::test_superuser_triggers_exception"""
        login = self.post(
            "/api/sales_admin/auth/otp/verify",
            json={
                "phone_number": SUPERUSER_PHONE,
                "otp": pyotp.TOTP(SUPERUSER_TOTP_SECRET).now(),
            },
        )
        assert login.status_code == 200
        response = self.get("/api/test-sentry/")
        assert response.status_code == 500
