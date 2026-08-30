"""ORM-backed tests for the sales-admin TOTP verification endpoint."""

from __future__ import annotations

from rest_framework.test import APIClient

from aggregator.models import City, Country, State
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
