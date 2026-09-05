"""ORM-backed tests for the Android app's token-only grouped city list.

The bearer-token counterpart of ``tests/test_city_utilities.py`` (the web
session, superuser-only endpoint) -- here any authenticated sales person may
look up cities, since the mobile app needs the picker for its own forms.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Country, State
from authentication.models import SalesPerson
from tests.android.common import AndroidApiTestCase

User = get_user_model()

URL = "/android/api/v1/utilities/cities"


class AndroidCitiesTest(AndroidApiTestCase):
    """Cover the Android grouped city list endpoint.

    tests/android/test_cities.py::AndroidCitiesTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        cls.country = Country.objects.create(
            name="India", iso_code="IN", created_by=cls.superuser
        )
        cls.state = State.objects.create(
            name="Maharashtra", code="MH", country=cls.country, created_by=cls.superuser
        )
        cls.pune = City.objects.create(name="Pune", state=cls.state, created_by=cls.superuser)
        cls.salesperson = SalesPerson.objects.create(
            user=User.objects.create_user(
                phone_number="7777777777",
                name="salesperson",
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            ),
            city=cls.pune,
            created_by=cls.superuser,
        )

    def test_cities_requires_a_salesperson_token(self):
        """tests/android/test_cities.py::AndroidCitiesTest::test_cities_requires_a_salesperson_token"""
        self.assertIn(self.client.get(URL).status_code, (401, 403))
        # A superuser has no SalesPerson profile -> forbidden here too.
        self.login_as(self.superuser)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_403_FORBIDDEN)
        # A sales person's token works.
        self.login_as(self.salesperson.user)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_200_OK)

    def test_cities_grouped_by_state(self):
        """tests/android/test_cities.py::AndroidCitiesTest::test_cities_grouped_by_state"""
        self.login_as(self.salesperson.user)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data
        maharashtra = next(state for state in payload if state["name"] == "Maharashtra")
        pune = next(city for city in maharashtra["cities"] if city["name"] == "Pune")
        self.assertEqual(pune["id"], self.pune.id)

    def test_session_login_does_not_authenticate(self):
        """A browser session never authenticates the Android endpoint.

        tests/android/test_cities.py::AndroidCitiesTest::test_session_login_does_not_authenticate
        """
        self.client.force_login(self.salesperson.user)
        self.assertEqual(self.client.get(URL).status_code, 401)
