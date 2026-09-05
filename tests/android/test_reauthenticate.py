"""ORM-backed tests for the Android app's token-only ``auth/reauthenticate``.

The bearer-token counterpart of ``tests/test_reauthenticate.py`` (the web
session endpoint).
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.authtoken.models import Token

from aggregator.models import City, Country, State
from authentication.models import SalesPerson, User
from tests.android.common import AndroidApiTestCase

URL = "/android/api/v1/auth/reauthenticate"


class AndroidReauthenticateTest(AndroidApiTestCase):
    """Verify the Android reauth endpoint's contract.

    tests/android/test_reauthenticate.py::AndroidReauthenticateTest
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
        """tests/android/test_reauthenticate.py::AndroidReauthenticateTest::test_anonymous_gets_401"""
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_fresh_token_is_accepted(self):
        """tests/android/test_reauthenticate.py::AndroidReauthenticateTest::test_fresh_token_is_accepted"""
        self.login_as(self.salesperson.user)

        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["user"]["id"], self.salesperson.user.id)
        self.assertEqual(response.data["user"]["role"], "salesperson")

    def test_expired_token_is_rejected_and_deleted(self):
        """tests/android/test_reauthenticate.py::AndroidReauthenticateTest::test_expired_token_is_rejected_and_deleted"""
        token = self.login_as(self.salesperson.user)
        Token.objects.filter(key=token.key).update(created=timezone.now() - timedelta(hours=48))

        response = self.client.get(URL)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_non_salesperson_token_is_rejected(self):
        """A token for a user with no SalesPerson profile is refused (403).

        tests/android/test_reauthenticate.py::AndroidReauthenticateTest::test_non_salesperson_token_is_rejected
        """
        self.login_as(self.superuser)
        self.assertEqual(self.client.get(URL).status_code, 403)

    def test_session_login_is_rejected(self):
        """A browser session never authenticates the Android endpoint (token-only).

        tests/android/test_reauthenticate.py::AndroidReauthenticateTest::test_session_login_is_rejected
        """
        self.client.force_login(self.salesperson.user)
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_token_expiry_is_fixed_from_creation_not_sliding(self):
        """The 24h TTL is measured from ``Token.created`` and never extended.

        ``ExpiringTokenAuthentication`` (api/authentication.py) checks
        ``token.created`` on every request but never updates it -- unlike a
        sliding-window scheme, using the token does not push its expiry out.
        A token aged to just under 24h stays valid right up to that boundary
        regardless of how many requests were made against it in between.

        tests/android/test_reauthenticate.py::AndroidReauthenticateTest::test_token_expiry_is_fixed_from_creation_not_sliding
        """
        token = self.login_as(self.salesperson.user)
        created_at_login = token.created

        # Several requests against the token must not touch ``created``.
        for _ in range(3):
            self.assertEqual(self.client.get(URL).status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.created, created_at_login)

        # Age it to just under the 24h boundary: still valid...
        Token.objects.filter(key=token.key).update(
            created=timezone.now() - timedelta(hours=23, minutes=59)
        )
        self.assertEqual(self.client.get(URL).status_code, 200)
        # ...and that request did not reset the clock either.
        token.refresh_from_db()
        self.assertLess(token.created, timezone.now() - timedelta(hours=23, minutes=58))
