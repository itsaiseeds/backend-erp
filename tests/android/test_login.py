"""ORM-backed tests for the sales-person Android app's TOTP login endpoint.

The token counterpart of ``tests/test_verify_otp_view.py`` (the web session
login) -- this endpoint mints a bearer token and never touches sessions.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.authtoken.models import Token

from aggregator.models import City, Country, State
from authentication.models import SalesPerson, User
from tests.android.common import AndroidApiTestCase

URL = "/android/api/v1/auth/login"


class AndroidLoginTest(AndroidApiTestCase):
    """Cover successful and rejected Android sales-person TOTP login.

    Login is what issues the token in the first place, so this suite calls
    the endpoint directly rather than through the base class's ``login_as``.

    tests/android/test_login.py::AndroidLoginTest
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
        salesperson_user = User.objects.create_user(
            phone_number="7777777777",
            name="salesperson",
            totp_secret="KRSXG5DSNFXGOIDB",
            totp_enabled=True,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        cls.salesperson = SalesPerson.objects.create(
            user=salesperson_user,
            city=city,
            created_by=cls.superuser,
        )

    def setUp(self):
        super().setUp()
        cache.clear()  # reset the android_login per-IP throttle counter

    def _login(self, phone: str, otp: str):
        return self.client.post(URL, {"phone_number": phone, "otp": otp}, format="json")

    def test_salesperson_can_login_and_receive_a_token(self):
        """tests/android/test_login.py::AndroidLoginTest::test_salesperson_can_login_and_receive_a_token"""
        response = self._login(
            self.salesperson.user.phone_number, self.salesperson.user.totp.now()
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data["token"])
        self.assertEqual(
            response.data["user"]["phone_number"], self.salesperson.user.phone_number
        )
        self.assertEqual(response.data["user"]["role"], "salesperson")
        # Session-only surfaces stay untouched.
        self.assertNotIn("sessionid", response.cookies)

    def test_non_salesperson_cannot_login(self):
        """A superuser (no SalesPerson profile) is refused on the Android login.

        tests/android/test_login.py::AndroidLoginTest::test_non_salesperson_cannot_login
        """
        response = self._login(self.superuser.phone_number, self.superuser.totp.now())
        self.assertEqual(response.status_code, 400)

    def test_invalid_otp_is_rejected(self):
        """tests/android/test_login.py::AndroidLoginTest::test_invalid_otp_is_rejected"""
        response = self._login(self.salesperson.user.phone_number, "000000")
        self.assertEqual(response.status_code, 400)

    def test_token_rotates_on_relogin(self):
        """A fresh login invalidates the previous token.

        tests/android/test_login.py::AndroidLoginTest::test_token_rotates_on_relogin
        """
        Token.objects.filter(user=self.salesperson.user).delete()
        stale = Token.objects.create(user=self.salesperson.user)
        stale_key = stale.key

        response = self._login(
            self.salesperson.user.phone_number, self.salesperson.user.totp.now()
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotEqual(response.data["token"], stale_key)
        self.assertFalse(Token.objects.filter(key=stale_key).exists())

    def test_account_locks_after_five_failed_attempts(self):
        """tests/android/test_login.py::AndroidLoginTest::test_account_locks_after_five_failed_attempts"""
        for _ in range(5):
            self.assertEqual(
                self._login(self.salesperson.user.phone_number, "000000").status_code, 400
            )

        self.salesperson.user.refresh_from_db()
        self.assertTrue(self.salesperson.user.is_totp_locked())

    def test_locked_account_refuses_even_correct_code(self):
        """tests/android/test_login.py::AndroidLoginTest::test_locked_account_refuses_even_correct_code"""
        self.salesperson.user.totp_lockout_until = timezone.now() + timedelta(minutes=5)
        self.salesperson.user.save(update_fields=["totp_lockout_until"])

        response = self._login(
            self.salesperson.user.phone_number, self.salesperson.user.totp.now()
        )
        self.assertEqual(response.status_code, 400)
