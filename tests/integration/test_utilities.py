"""Integration tests for the ``/api/utilities/`` helpers (look-ups).

These are public endpoints, so no authorization header is needed. The
``dml.sql`` baseline seeds a single city, Pune, under Maharashtra.
"""

from __future__ import annotations

import pytest

from tests.integration.base import IntegrationTestCase

pytestmark = pytest.mark.integration


class UtilitiesTest(IntegrationTestCase):
    """Covers the state -> cities look-up endpoint.
    tests/integration/test_utilities.py::UtilitiesTest
    """

    def test_cities_for_state_returns_pune(self):
        """tests/integration/test_utilities.py::UtilitiesTest::test_cities_for_state_returns_pune"""
        response = self.get(
            "/api/utilities/cities", params={"state": "Maharashtra"}
        )
        assert response.status_code == 200
        cities = response.json()
        assert isinstance(cities, list)
        assert {"id": 1, "name": "Pune"} in cities

    def test_public_no_auth_needed(self):
        """tests/integration/test_utilities.py::UtilitiesTest::test_public_no_auth_needed"""
        self.client.headers.pop("Authorization", None)
        response = self.get(
            "/api/utilities/cities", params={"state": "maharashtra"}
        )
        assert response.status_code == 200

    def test_unknown_state_returns_404(self):
        """tests/integration/test_utilities.py::UtilitiesTest::test_unknown_state_returns_404"""
        response = self.get(
            "/api/utilities/cities", params={"state": "No Such State"}
        )
        assert response.status_code == 404

    def test_missing_state_returns_400(self):
        """tests/integration/test_utilities.py::UtilitiesTest::test_missing_state_returns_400"""
        response = self.get("/api/utilities/cities")
        assert response.status_code == 400
