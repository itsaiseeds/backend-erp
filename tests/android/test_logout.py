"""ORM-backed tests for ``POST /android/api/v1/auth/logout``.

The bearer-token counterpart of ``tests/test_logout.py`` (the web session
logout) -- this only deletes the caller's ``Token`` row and never touches
sessions.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from aggregator.models import City, Country, State
from authentication.models import SalesPerson
from tests.android.common import AndroidApiTestCase

User = get_user_model()

URL = "/android/api/v1/auth/logout"


class AndroidLogoutTest(AndroidApiTestCase):
    """Cover token invalidation and permission gating.

    tests/android/test_logout.py::AndroidLogoutTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        country = Country.objects.create(
            name="Test Country", iso_code="TST", created_by=cls.superuser
        )
        state = State.objects.create(
            name="Test State", code="TS", country=country, created_by=cls.superuser
        )
        city = City.objects.create(name="Test City", state=state, created_by=cls.superuser)
        cls.salesperson = SalesPerson.objects.create(
            user=User.objects.create_user(
                phone_number="7777777777",
                name="salesperson",
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            ),
            city=city,
            created_by=cls.superuser,
        )

    def test_anonymous_gets_401(self):
        """tests/android/test_logout.py::AndroidLogoutTest::test_anonymous_gets_401"""
        self.assertEqual(self.client.post(URL).status_code, 401)

    def test_token_is_revoked(self):
        """The caller's Token row is deleted and reuse returns 401.

        tests/android/test_logout.py::AndroidLogoutTest::test_token_is_revoked
        """
        token = self.login_as(self.salesperson.user)

        response = self.client.post(URL)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

        followup = self.client.get("/android/api/v1/auth/reauthenticate")
        self.assertEqual(followup.status_code, 401)

    def test_session_login_does_not_authenticate(self):
        """A browser session never authenticates the Android logout endpoint.

        tests/android/test_logout.py::AndroidLogoutTest::test_session_login_does_not_authenticate
        """
        self.client.force_login(self.salesperson.user)
        self.assertEqual(self.client.post(URL).status_code, 401)
