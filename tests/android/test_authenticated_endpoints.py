"""The Android endpoints a logged-in sales person calls: reauthenticate, logout
and the grouped city picker.

All three need the same fixture (a DML-seeded superuser, a geography tree and
one sales person) and one bearer token, so they share a class -- and therefore
a single ``dml.sql`` load -- rather than repeating it per endpoint module.

Who may call them is not tested here: ``AndroidBaseView`` fixes the credential
scheme and the ``SalesPerson`` requirement for every Android view, and that is
pinned once in ``tests/test_view_contracts.py``. What is tested here is what
each endpoint *does* once a valid token is presented. Login itself lives in
``tests/android/test_login.py`` -- it is what mints the token.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token

from aggregator.models import City, Country, State
from authentication.models import SalesPerson, User
from tests.android.common import AndroidApiTestCase

REAUTHENTICATE_URL = "/android/api/v1/auth/reauthenticate"
LOGOUT_URL = "/android/api/v1/auth/logout"
CITIES_URL = "/android/api/v1/utilities/cities"


class AndroidAuthenticatedEndpointsTest(AndroidApiTestCase):
    """Cover the behaviour of the token-authenticated Android endpoints.

    tests/android/test_authenticated_endpoints.py::AndroidAuthenticatedEndpointsTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.superuser}
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

    # -- reauthenticate -------------------------------------------------------

    def test_reauthenticate_identifies_the_token_holder(self):
        """tests/android/test_authenticated_endpoints.py::AndroidAuthenticatedEndpointsTest::test_reauthenticate_identifies_the_token_holder"""
        self.login_as(self.salesperson.user)

        response = self.client.get(REAUTHENTICATE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["user"]["id"], self.salesperson.user.id)
        self.assertEqual(response.data["user"]["role"], "salesperson")

    def test_token_expiry_is_fixed_from_creation_not_sliding(self):
        """The 24h TTL is measured from ``Token.created`` and never extended.

        ``ExpiringTokenAuthentication`` (api/authentication.py) checks
        ``token.created`` on every request but never updates it -- unlike a
        sliding-window scheme, using the token does not push its expiry out.
        A token aged to just under 24h stays valid right up to that boundary
        regardless of how many requests were made against it in between.
        (Rejection *past* the boundary is covered by
        ``tests/test_view_contracts.py::TokenAuthContractTest``.)

        tests/android/test_authenticated_endpoints.py::AndroidAuthenticatedEndpointsTest::test_token_expiry_is_fixed_from_creation_not_sliding
        """
        token = self.login_as(self.salesperson.user)
        created_at_login = token.created

        # Several requests against the token must not touch ``created``.
        for _ in range(3):
            self.assertEqual(self.client.get(REAUTHENTICATE_URL).status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.created, created_at_login)

        # Age it to just under the 24h boundary: still valid...
        Token.objects.filter(key=token.key).update(
            created=timezone.now() - timedelta(hours=23, minutes=59)
        )
        self.assertEqual(self.client.get(REAUTHENTICATE_URL).status_code, 200)
        # ...and that request did not reset the clock either.
        token.refresh_from_db()
        self.assertLess(token.created, timezone.now() - timedelta(hours=23, minutes=58))

    # -- logout ---------------------------------------------------------------

    def test_logout_revokes_the_token(self):
        """The caller's Token row is deleted and reuse returns 401.

        tests/android/test_authenticated_endpoints.py::AndroidAuthenticatedEndpointsTest::test_logout_revokes_the_token
        """
        token = self.login_as(self.salesperson.user)

        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

        self.assertEqual(self.client.get(REAUTHENTICATE_URL).status_code, 401)

    # -- utilities ------------------------------------------------------------

    def test_cities_are_grouped_by_state(self):
        """The web counterpart is tests/test_geography_utilities.py.

        tests/android/test_authenticated_endpoints.py::AndroidAuthenticatedEndpointsTest::test_cities_are_grouped_by_state
        """
        self.login_as(self.salesperson.user)

        response = self.client.get(CITIES_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        maharashtra = next(state for state in response.data if state["name"] == "Maharashtra")
        self.assertEqual(maharashtra["id"], self.state.id)
        pune = next(city for city in maharashtra["cities"] if city["name"] == "Pune")
        self.assertEqual(pune["id"], self.pune.id)
