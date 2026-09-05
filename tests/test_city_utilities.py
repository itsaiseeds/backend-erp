"""ORM-backed tests for the superuser-only grouped city list utility endpoint.

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``) and add
their own geography + an application admin in ``setUpTestData``. Request/response
flows are exercised over the test :class:`~rest_framework.test.APIClient` with a
logged-in session, since this is a session-only web endpoint (see
``tests/android/test_cities.py`` for the Android token-based counterpart).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Country, State
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class CityUtilitiesTest(WebApiTestCase):
    """Cover the superuser-only grouped city list endpoint.

    tests/test_city_utilities.py::CityUtilitiesTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.seed_admin = User.objects.create_user(
            phone_number="7777777777",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=cls.seed_admin, can_update_stock_count=True, created_by=cls.superuser
        )
        cls.country = Country.objects.create(name="India", iso_code="IN", created_by=cls.superuser)
        cls.state = State.objects.create(
            name="Maharashtra", code="MH", country=cls.country, created_by=cls.superuser
        )
        cls.pune = City.objects.create(name="Pune", state=cls.state, created_by=cls.superuser)

    def test_cities_requires_superuser(self):
        """tests/test_city_utilities.py::CityUtilitiesTest::test_cities_requires_superuser"""
        # Anonymous
        self.assertIn(self.client.get("/api/utilities/cities").status_code, (401, 403))
        # App admin is still forbidden (superuser only).
        self.login_as(self.seed_admin)
        self.assertIn(self.client.get("/api/utilities/cities").status_code, (401, 403))
        # Superuser is allowed.
        self.login_as(self.superuser)
        self.assertEqual(self.client.get("/api/utilities/cities").status_code, status.HTTP_200_OK)

    def test_cities_grouped_by_state(self):
        """tests/test_city_utilities.py::CityUtilitiesTest::test_cities_grouped_by_state"""
        self.login_as(self.superuser)
        response = self.client.get("/api/utilities/cities")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data
        self.assertIsInstance(payload, list)
        self.assertTrue(any(state["name"] == "Maharashtra" for state in payload))
        maharashtra = next(state for state in payload if state["name"] == "Maharashtra")
        self.assertIn("id", maharashtra)
        self.assertTrue(any(city["name"] == "Pune" for city in maharashtra["cities"]))
        pune = next(city for city in maharashtra["cities"] if city["name"] == "Pune")
        self.assertEqual(pune["id"], self.pune.id)
