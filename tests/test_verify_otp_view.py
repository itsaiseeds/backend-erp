"""ORM-backed tests for the sales-admin TOTP verification endpoint."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator.models import City, Country, State
from api.sales_admin.VerifyOTPView import VerifyOTPThrottle
from authentication.models import SalesPerson, User
from tests.common import DMLTestCase


class VerifyOTPTest(DMLTestCase):
    """Cover successful and rejected sales-admin TOTP verification.

    tests/test_verify_otp_view.py::VerifyOTPTest
    """

    @classmethod
    def setUpTestData(cls):
        """Create validly enrolled normal and salesperson accounts for this class."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        cls.normal_user = User.objects.create_user(
            phone_number="5555555555",
            name="normal user",
            totp_secret="KRSXG5DSNFXGOIDB",
            totp_enabled=True,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        cls.unenrolled_user = User.objects.get(phone_number="8888888888")
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
        """Create an unauthenticated API client for every test in this class."""
        self.client = APIClient()
        # DRF throttles store per-IP counters in the default cache; without
        # clearing between tests one test's requests would count against the
        # next test's budget on the shared 127.0.0.1 origin.
        cache.clear()

    def test_superuser_can_verify_otp_and_receive_credentials(self):
        """tests/test_verify_otp_view.py::VerifyOTPTest::test_superuser_can_verify_otp_and_receive_credentials"""
        response = self.client.post(
            "/api/sales_admin/auth/otp/verify",
            {
                "phone_number": self.superuser.phone_number,
                "otp": self.superuser.totp.now(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["token"])
        self.assertEqual(response.data["user"]["phone_number"], self.superuser.phone_number)
        self.assertTrue(response.data["can_create_admin"])
        self.assertTrue(response.data["can_create_sales_person"])

    def test_invalid_otp_is_rejected(self):
        """tests/test_verify_otp_view.py::VerifyOTPTest::test_invalid_otp_is_rejected"""
        response = self.client.post(
            "/api/sales_admin/auth/otp/verify",
            {"phone_number": self.superuser.phone_number, "otp": "000000"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_unenrolled_user_cannot_verify_otp(self):
        """tests/test_verify_otp_view.py::VerifyOTPTest::test_unenrolled_user_cannot_verify_otp"""
        response = self.client.post(
            "/api/sales_admin/auth/otp/verify",
            {"phone_number": self.unenrolled_user.phone_number, "otp": "000000"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_normal_user_cannot_verify_otp(self):
        """tests/test_verify_otp_view.py::VerifyOTPTest::test_normal_user_cannot_verify_otp"""
        response = self.client.post(
            "/api/sales_admin/auth/otp/verify",
            {
                "phone_number": self.normal_user.phone_number,
                "otp": self.normal_user.totp.now(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_salesperson_cannot_verify_otp(self):
        """tests/test_verify_otp_view.py::VerifyOTPTest::test_salesperson_cannot_verify_otp"""
        response = self.client.post(
            "/api/sales_admin/auth/otp/verify",
            {
                "phone_number": self.salesperson.user.phone_number,
                "otp": self.salesperson.user.totp.now(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    # -- Security hardening --------------------------------------------------

    def _verify(self, phone: str, otp: str):
        return self.client.post(
            "/api/sales_admin/auth/otp/verify",
            {"phone_number": phone, "otp": otp},
            format="json",
        )

    def test_replayed_otp_is_rejected(self):
        """A code accepted once cannot be reused inside its window.

        tests/test_verify_otp_view.py::VerifyOTPTest::test_replayed_otp_is_rejected
        """
        code = self.superuser.totp.now()
        first = self._verify(self.superuser.phone_number, code)
        self.assertEqual(first.status_code, 200, first.content)

        second = self._verify(self.superuser.phone_number, code)
        self.assertEqual(second.status_code, 400)

    def test_account_locks_after_five_failed_attempts(self):
        """Five wrong codes flip the lockout on; the sixth attempt stays 400.

        Locked-out responses reuse the generic 400 body so a caller cannot
        distinguish "you are locked" from "code was wrong" — that distinction
        leaks account existence.

        tests/test_verify_otp_view.py::VerifyOTPTest::test_account_locks_after_five_failed_attempts
        """
        for _ in range(5):
            self.assertEqual(self._verify(self.superuser.phone_number, "000000").status_code, 400)

        response = self._verify(self.superuser.phone_number, "000000")
        self.assertEqual(response.status_code, 400)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_totp_locked())

    def test_locked_account_refuses_even_correct_code(self):
        """A caller who is locked out cannot log in even with a valid code.

        tests/test_verify_otp_view.py::VerifyOTPTest::test_locked_account_refuses_even_correct_code
        """
        self.superuser.totp_lockout_until = timezone.now() + timedelta(minutes=5)
        self.superuser.save(update_fields=["totp_lockout_until"])

        response = self._verify(self.superuser.phone_number, self.superuser.totp.now())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Invalid phone number or TOTP code.")

    def test_expired_lockout_lets_valid_code_through(self):
        """Once the lockout window has passed a valid code is accepted again.

        tests/test_verify_otp_view.py::VerifyOTPTest::test_expired_lockout_lets_valid_code_through
        """
        self.superuser.totp_lockout_until = timezone.now() - timedelta(minutes=1)
        self.superuser.save(update_fields=["totp_lockout_until"])

        response = self._verify(self.superuser.phone_number, self.superuser.totp.now())
        self.assertEqual(response.status_code, 200, response.content)

    def test_successful_login_resets_failure_counter(self):
        """A valid TOTP after some wrong ones zeros the strike counter.

        tests/test_verify_otp_view.py::VerifyOTPTest::test_successful_login_resets_failure_counter
        """
        for _ in range(3):
            self._verify(self.superuser.phone_number, "000000")
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.failed_totp_attempts, 3)

        response = self._verify(self.superuser.phone_number, self.superuser.totp.now())
        self.assertEqual(response.status_code, 200, response.content)
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.failed_totp_attempts, 0)
        self.assertIsNone(self.superuser.totp_lockout_until)

    def test_per_ip_throttle_kicks_in(self):
        """DRF's per-IP throttle returns 429 after the configured rate.

        Pins ``VerifyOTPThrottle.rate`` at the class level to 3/min so the
        test does not depend on the production budget. Setting ``rate`` at
        the class short-circuits ``SimpleRateThrottle.__init__``'s lookup of
        the (import-time cached) ``THROTTLE_RATES`` dict, which is why
        ``override_settings(REST_FRAMEWORK=...)`` cannot flex this rate.

        tests/test_verify_otp_view.py::VerifyOTPTest::test_per_ip_throttle_kicks_in
        """
        with patch.object(VerifyOTPThrottle, "rate", "3/min", create=True):
            # Three requests inside the budget: each is answered on its own
            # merits (400 for a wrong code).
            for _ in range(3):
                self.assertEqual(
                    self._verify(self.superuser.phone_number, "000000").status_code,
                    400,
                )
            # The fourth is throttled before it ever reaches our view logic.
            self.assertEqual(self._verify(self.superuser.phone_number, "000000").status_code, 429)

    def test_generic_400_for_unknown_and_locked(self):
        """Unknown phone and locked-out user return the exact same body.

        tests/test_verify_otp_view.py::VerifyOTPTest::test_generic_400_for_unknown_and_locked
        """
        self.superuser.totp_lockout_until = timezone.now() + timedelta(minutes=5)
        self.superuser.save(update_fields=["totp_lockout_until"])

        locked = self._verify(self.superuser.phone_number, self.superuser.totp.now())
        unknown = self._verify("1231231234", "000000")

        self.assertEqual(locked.status_code, unknown.status_code)
        self.assertEqual(locked.data, unknown.data)

    def test_token_rotates_on_relogin(self):
        """A fresh login invalidates the previous DRF token.

        tests/test_verify_otp_view.py::VerifyOTPTest::test_token_rotates_on_relogin
        """
        Token.objects.filter(user=self.superuser).delete()
        stale = Token.objects.create(user=self.superuser)
        stale_key = stale.key

        response = self._verify(self.superuser.phone_number, self.superuser.totp.now())
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotEqual(response.data["token"], stale_key)
        self.assertFalse(Token.objects.filter(key=stale_key).exists())
