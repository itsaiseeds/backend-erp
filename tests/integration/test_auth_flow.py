"""Endpoint integration tests for the sales_admin OTP auth flow.

These hit the live Django server over HTTP via the class-based helpers in
:mod:`tests.integration.base`. The ``django_test`` database is seeded by
sql/dml.sql with a superuser whose phone number is 9999999999.
"""

# How to run (from the project root). All of these run INSIDE the web
# container, so the host Python never needs Django:
#   bash scripts/run.sh test-integration
#   bash scripts/run.sh test-integration tests/integration/test_auth_flow.py::AuthFlowTest
#   bash scripts/run.sh test-integration tests/integration/test_auth_flow.py::AuthFlowTest::test_generate_otp_returns_200  # noqa: E501
#
# The same pytest node strings work ad hoc inside the container:
#   docker compose exec -T web python -m pytest tests/integration/test_auth_flow.py::AuthFlowTest::test_generate_otp_returns_200 -v  # noqa: E501

from __future__ import annotations

import pytest

from tests.integration.base import IntegrationTestCase

pytestmark = pytest.mark.integration

SUPERUSER_PHONE = "9999999999"


class AuthFlowTest(IntegrationTestCase):
    """Covers the OTP request + verify endpoints of the sales admin API.
    tests/integration/test_auth_flow.py::AuthFlowTest
    """

    def test_generate_otp_returns_200(self):
        """tests/integration/test_auth_flow.py::AuthFlowTest::test_generate_otp_returns_200"""
        response = self.post(
            "/api/sales_admin/auth/otp/request",
            json={"phone_number": SUPERUSER_PHONE},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["phone_number"] == SUPERUSER_PHONE
        assert payload["sent"] is True

    def test_verify_otp_requires_valid_otp(self):
        """tests/integration/test_auth_flow.py::AuthFlowTest::test_verify_otp_requires_valid_otp"""
        response = self.post(
            "/api/sales_admin/auth/otp/verify",
            json={"phone_number": SUPERUSER_PHONE, "otp": "000000"},
        )
        assert response.status_code == 400
