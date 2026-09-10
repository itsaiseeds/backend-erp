"""ORM-backed tests for the superuser-only countries and states utility endpoints.

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone
``9999999999``) and add their own geography in ``setUpTestData``. Request/
response flows are exercised over the test :class:`~rest_framework.test.APIClient`
with a logged-in session, since these are session-only web endpoints.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Country, State
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class GeographyUtilitiesTest(WebApiTestCase):
    """Cover the superuser-only countries and states list endpoints.

    tests/test_geography_utilities.py::GeographyUtilitiesTest
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
        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.superuser}
        )
        cls.state = State.objects.create(
            name="Maharashtra", code="MH", country=cls.country, created_by=cls.superuser
        )
        cls.pune = City.objects.create(name="Pune", state=cls.state, created_by=cls.superuser)

    def test_countries_requires_superuser(self):
        """tests/test_geography_utilities.py::GeographyUtilitiesTest::test_countries_requires_superuser"""
        # Anonymous
        self.assertIn(self.client.get("/api/utilities/countries").status_code, (401, 403))
        # App admin is still forbidden (superuser only).
        self.login_as(self.seed_admin)
        self.assertIn(self.client.get("/api/utilities/countries").status_code, (401, 403))
        # Superuser is allowed.
        self.login_as(self.superuser)
        self.assertEqual(self.client.get("/api/utilities/countries").status_code, status.HTTP_200_OK)

    def test_countries_list(self):
        """tests/test_geography_utilities.py::GeographyUtilitiesTest::test_countries_list"""
        self.login_as(self.superuser)
        response = self.client.get("/api/utilities/countries")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data
        self.assertIsInstance(payload, list)
        self.assertTrue(any(c["name"] == "India" for c in payload))
        india = next(c for c in payload if c["name"] == "India")
        self.assertEqual(india["id"], self.country.id)
        self.assertEqual(india["iso_code"], "IN")

    def test_states_requires_superuser(self):
        """tests/test_geography_utilities.py::GeographyUtilitiesTest::test_states_requires_superuser"""
        # Anonymous
        self.assertIn(self.client.get("/api/utilities/states").status_code, (401, 403))
        # App admin is still forbidden (superuser only).
        self.login_as(self.seed_admin)
        self.assertIn(self.client.get("/api/utilities/states").status_code, (401, 403))
        # Superuser is allowed.
        self.login_as(self.superuser)
        self.assertEqual(self.client.get("/api/utilities/states").status_code, status.HTTP_200_OK)

    def test_states_list(self):
        """tests/test_geography_utilities.py::GeographyUtilitiesTest::test_states_list"""
        self.login_as(self.superuser)
        response = self.client.get("/api/utilities/states")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data
        self.assertIsInstance(payload, list)
        self.assertTrue(any(s["name"] == "Maharashtra" for s in payload))
        maharashtra = next(s for s in payload if s["name"] == "Maharashtra")
        self.assertEqual(maharashtra["id"], self.state.id)
        self.assertEqual(maharashtra["code"], "MH")
        self.assertEqual(maharashtra["country"]["id"], self.country.id)
        self.assertEqual(maharashtra["country"]["name"], "India")

    def test_states_filtered_by_country(self):
        """tests/test_geography_utilities.py::GeographyUtilitiesTest::test_states_filtered_by_country"""
        self.login_as(self.superuser)
        response = self.client.get("/api/utilities/states", {"country": self.country.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data
        self.assertTrue(payload)
        self.assertTrue(all(s["country"]["id"] == self.country.id for s in payload))

        unknown = self.client.get("/api/utilities/states", {"country": 999999})
        self.assertEqual(unknown.status_code, status.HTTP_200_OK)
        self.assertEqual(unknown.data, [])
