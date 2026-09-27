"""Losing a role, or what a login was granted on, ends every session and token.

Covers three audit findings together, because they are one story:

* a soft-deleted ``Admin`` / ``SalesPerson`` profile confers no role
  (``User.is_admin_user`` / ``is_salesperson`` / ``live_admin_profile``);
* soft-deleting a profile, deactivating a user, changing the login phone
  number or rotating the TOTP secret revokes the user's web sessions and bearer
  tokens (``authentication.credentials.revoke_user_credentials``), and the two
  login views refuse inactive users;
* an app admin may not edit or delete another admin's (or a superuser's)
  fallback sales-person profile through ``/api/sales-admin/sales-people/<id>``.

Run: bash scripts/run.sh test-serial tests/test_credential_revocation.py
"""

from __future__ import annotations

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator.InventoryOperations import _assert_can_update_stock_count
from aggregator.models import City, Country, State
from authentication.models import Admin, SalesPerson, User
from tests.common import WebApiTestCase

SUPERUSER_PHONE = "9999999999"
TOTP_SECRET = "KRSXG5DSNFXGOIDB"

ADMIN_URL = "/api/sales-admin/admins/{id}"
SALESPERSON_URL = "/api/sales-admin/sales-people/{id}"
ADMIN_ONLY_URL = "/api/utilities/countries"
WEB_LOGIN_URL = "/api/sales-admin/auth/otp/verify"
ANDROID_LOGIN_URL = "/android/api/v1/auth/login"


class CredentialRevocationTest(WebApiTestCase):
    """tests/test_credential_revocation.py::CredentialRevocationTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.superuser}
        )
        state = State.objects.create(
            name="Maharashtra", code="MH", country=country, created_by=cls.superuser
        )
        cls.city = City.objects.create(name="Pune", state=state, created_by=cls.superuser)

        # An admin carrying the fallback SalesPerson profile AdminsView creates.
        cls.admin_user = cls._user("7777777777", "app admin")
        cls.admin = Admin.objects.create(
            user=cls.admin_user, can_update_stock_count=True, created_by=cls.superuser
        )
        cls.admin_fallback = SalesPerson.objects.create(
            user=cls.admin_user, city=cls.city, created_by=cls.superuser
        )
        cls.other_admin_user = cls._user("7777777776", "other admin")
        Admin.objects.create(user=cls.other_admin_user, created_by=cls.superuser)

        cls.salesperson_user = cls._user("5555555555", "sales person")
        cls.salesperson = SalesPerson.objects.create(
            user=cls.salesperson_user, city=cls.city, created_by=cls.superuser
        )

    @staticmethod
    def _user(phone: str, name: str) -> User:
        superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        return User.objects.create_user(
            phone_number=phone,
            name=name,
            totp_secret=TOTP_SECRET,
            totp_enabled=True,
            is_verified=True,
            created_by=superuser,
            verified_by=superuser,
        )

    # -- helpers --------------------------------------------------------------

    def _grant_credentials(self, user: User) -> None:
        """Give ``user`` a live web session and a bearer token."""
        APIClient().force_login(user)
        Token.objects.create(user=user)
        self.assertTrue(self._has_credentials(user))

    def _has_credentials(self, user: User) -> bool:
        sessions = [
            s for s in Session.objects.all() if s.get_decoded().get(SESSION_KEY) == str(user.pk)
        ]
        return bool(sessions) or Token.objects.filter(user=user).exists()

    def _fresh(self, user: User) -> User:
        return User.objects.get(id=user.id)

    # -- soft-deleted profiles confer no role ---------------------------------

    def test_a_soft_deleted_profile_confers_no_role(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_a_soft_deleted_profile_confers_no_role"""
        self.admin.delete(deleted_by=self.superuser)
        self.salesperson.mark_deleted(self.superuser)

        admin_user = self._fresh(self.admin_user)
        self.assertFalse(admin_user.is_admin_user)
        self.assertIsNone(admin_user.live_admin_profile)
        self.assertEqual(admin_user.role, "salesperson")  # the fallback is still live
        self.assertFalse(self._fresh(self.salesperson_user).is_salesperson)

        # Even a session opened after the deletion is refused by admin endpoints.
        self.login_as(admin_user)
        self.assertEqual(self.client.get(ADMIN_ONLY_URL).status_code, status.HTTP_403_FORBIDDEN)

    def test_a_deleted_admin_can_no_longer_log_in_or_count_stock(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_a_deleted_admin_can_no_longer_log_in_or_count_stock"""
        self.admin.delete(deleted_by=self.superuser)
        admin_user = self._fresh(self.admin_user)

        resp = self.client.post(
            WEB_LOGIN_URL,
            {"phone_number": admin_user.phone_number, "otp": admin_user.totp.now()},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        with self.assertRaises(PermissionDenied):
            _assert_can_update_stock_count(admin_user)

    def test_a_deleted_sales_person_can_no_longer_log_in_to_android(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_a_deleted_sales_person_can_no_longer_log_in_to_android"""
        self.salesperson.mark_deleted(self.superuser)
        user = self._fresh(self.salesperson_user)

        resp = self.client.post(
            ANDROID_LOGIN_URL,
            {"phone_number": user.phone_number, "otp": user.totp.now()},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # -- revocation -----------------------------------------------------------

    def test_deleting_a_profile_through_the_api_revokes_credentials(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_deleting_a_profile_through_the_api_revokes_credentials"""
        self._grant_credentials(self.admin_user)
        self._grant_credentials(self.salesperson_user)

        self.login_as(self.superuser)
        resp = self.client.delete(ADMIN_URL.format(id=self.admin.id))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self._has_credentials(self.admin_user))

        self.login_as(self.admin_user)
        resp = self.client.delete(SALESPERSON_URL.format(id=self.salesperson.id))
        # admin_user is no longer an admin, so the endpoint refuses them.
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.login_as(self.other_admin_user)
        resp = self.client.delete(SALESPERSON_URL.format(id=self.salesperson.id))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self._has_credentials(self.salesperson_user))

    def test_changing_a_credential_field_revokes_credentials(self):
        """Deactivation, a new phone number or a rotated TOTP secret logs the user out.

        tests/test_credential_revocation.py::CredentialRevocationTest::test_changing_a_credential_field_revokes_credentials
        """
        changes = {
            "is_active": lambda u: setattr(u, "is_active", False),
            "phone_number": lambda u: setattr(u, "phone_number", "5555555554"),
            "totp_secret": lambda u: u.generate_totp_secret(),
        }
        for field, change in changes.items():
            with self.subTest(field=field):
                user = self._fresh(self.salesperson_user)
                user.is_active = True
                user.save()
                self._grant_credentials(user)

                user = self._fresh(user)
                change(user)
                user.save()
                self.assertFalse(self._has_credentials(user))

    def test_changing_a_phone_number_through_the_api_revokes_credentials(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_changing_a_phone_number_through_the_api_revokes_credentials"""
        self._grant_credentials(self.salesperson_user)
        self.login_as(self.admin_user)

        resp = self.client.patch(
            SALESPERSON_URL.format(id=self.salesperson.id), {"name": "renamed"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertTrue(self._has_credentials(self.salesperson_user))

        resp = self.client.patch(
            SALESPERSON_URL.format(id=self.salesperson.id),
            {"phone_number": "5555555554"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertFalse(self._has_credentials(self.salesperson_user))

    def test_other_saves_keep_credentials(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_other_saves_keep_credentials"""
        self._grant_credentials(self.salesperson_user)
        user = self._fresh(self.salesperson_user)
        user.name = "renamed"
        user.save()
        # A field changed in memory but left out of update_fields is not saved.
        user.phone_number = "5555555554"
        user.save(update_fields=["name"])

        self.assertTrue(self._has_credentials(user))

    def test_inactive_users_cannot_log_in(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_inactive_users_cannot_log_in"""
        for url, user in (
            (WEB_LOGIN_URL, self.admin_user),
            (ANDROID_LOGIN_URL, self.salesperson_user),
        ):
            with self.subTest(url=url):
                user = self._fresh(user)
                user.is_active = False
                user.save()
                resp = self.client.post(
                    url, {"phone_number": user.phone_number, "otp": user.totp.now()}, format="json"
                )
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertFalse(self._has_credentials(user))

    # -- an admin cannot manage another admin through /sales-people/<id> ----

    def test_an_admin_cannot_touch_a_higher_roles_sales_person_profile(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_an_admin_cannot_touch_a_higher_roles_sales_person_profile"""
        superuser_fallback = SalesPerson.objects.create(
            user=self.superuser, city=self.city, created_by=self.superuser
        )
        self.login_as(self.other_admin_user)
        for profile in (self.admin_fallback, superuser_fallback):
            url = SALESPERSON_URL.format(id=profile.id)
            with self.subTest(target=profile.user.name):
                resp = self.client.patch(url, {"phone_number": "5555555553"}, format="json")
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)
                profile.refresh_from_db()
                profile.user.refresh_from_db()
                self.assertFalse(profile.is_deleted)
                self.assertNotEqual(profile.user.phone_number, "5555555553")

    def test_a_superuser_may_manage_an_admins_sales_person_profile(self):
        """tests/test_credential_revocation.py::CredentialRevocationTest::test_a_superuser_may_manage_an_admins_sales_person_profile"""
        Admin.objects.create(user=self.superuser, created_by=self.superuser)
        self.login_as(self.superuser)
        url = SALESPERSON_URL.format(id=self.admin_fallback.id)

        resp = self.client.patch(url, {"name": "renamed admin"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
