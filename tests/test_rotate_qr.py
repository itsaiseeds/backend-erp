"""Rotating a sales person's / godown manager's authenticator QR, and who may
see or delete an admin in the Django admin site.

Who may *call* the rotate endpoints is pinned in ``tests/test_view_contracts.py``
(``admin_required``); this file covers what they do and the admin-site rules.

tests/test_rotate_qr.py
"""

from __future__ import annotations

import pyotp
from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework import status

from aggregator.models import City, Country, State
from authentication.models import Admin, GodownManager, SalesPerson
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
SALESPERSON_URL = "/api/sales-admin/sales-people/{id}/rotate-qr"
GODOWN_URL = "/api/sales-admin/godown-managers/{id}/rotate-qr"


def _make_user(phone, name, creator):
    return User.objects.create_user(
        phone_number=phone,
        name=name,
        is_verified=True,
        created_by=creator,
        verified_by=creator,
        totp_secret=pyotp.random_base32(),
        totp_enabled=True,
    )


class RotateQrTest(WebApiTestCase):
    """tests/test_rotate_qr.py::RotateQrTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        # ``admin_required`` needs an Admin profile; a bare superuser is refused.
        Admin.objects.create(user=cls.superuser, created_by=cls.superuser)
        country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.superuser}
        )
        state = State.objects.create(name="Maharashtra", country=country, created_by=cls.superuser)
        city = City.objects.create(name="Pune", state=state, created_by=cls.superuser)

        cls.admin_user = _make_user("7777777777", "admin", cls.superuser)
        cls.admin = Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)
        cls.other_admin_user = _make_user("7777777778", "other admin", cls.superuser)
        cls.other_admin = Admin.objects.create(user=cls.other_admin_user, created_by=cls.superuser)
        SalesPerson.objects.create(user=cls.other_admin_user, city=city, created_by=cls.superuser)

        cls.salesperson = SalesPerson.objects.create(
            user=_make_user("5555555555", "sales", cls.superuser), city=city, created_by=cls.superuser
        )
        cls.manager = GodownManager.objects.create(
            user=_make_user("5555555556", "godown", cls.superuser), created_by=cls.superuser
        )

    def test_rotating_a_salesperson_replaces_the_secret(self):
        """tests/test_rotate_qr.py::RotateQrTest::test_rotating_a_salesperson_replaces_the_secret"""
        old = self.salesperson.user.totp_secret
        self.login_as(self.admin_user)

        response = self.client.post(SALESPERSON_URL.format(id=self.salesperson.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        user = User.objects.get(pk=self.salesperson.user_id)
        self.assertNotEqual(user.totp_secret, old)
        self.assertTrue(user.totp_enabled)
        self.assertEqual(
            response.data["totp"]["provisioning_uri"], user.totp_provisioning_uri()
        )

    def test_rotating_a_godown_manager_replaces_the_secret(self):
        """tests/test_rotate_qr.py::RotateQrTest::test_rotating_a_godown_manager_replaces_the_secret"""
        old = self.manager.user.totp_secret
        self.login_as(self.admin_user)

        response = self.client.post(GODOWN_URL.format(id=self.manager.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertNotEqual(User.objects.get(pk=self.manager.user_id).totp_secret, old)

    def test_an_admin_cannot_rotate_another_admins_fallback_profile(self):
        """tests/test_rotate_qr.py::RotateQrTest::test_an_admin_cannot_rotate_another_admins_fallback_profile"""
        fallback = self.other_admin_user.salesperson_profile
        old = self.other_admin_user.totp_secret
        self.login_as(self.admin_user)

        response = self.client.post(SALESPERSON_URL.format(id=fallback.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(User.objects.get(pk=self.other_admin_user.pk).totp_secret, old)

    def _list_totp(self, viewer):
        """``{phone_number: has totp}`` for the sales-people list as ``viewer``."""
        self.login_as(viewer)
        response = self.client.get("/api/sales-admin/sales-people")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        return {row["phone_number"]: "totp" in row for row in response.data}

    def test_an_admin_does_not_see_another_admins_qr_in_the_list(self):
        """tests/test_rotate_qr.py::RotateQrTest::test_an_admin_does_not_see_another_admins_qr_in_the_list"""
        shown = self._list_totp(self.admin_user)

        self.assertFalse(shown[self.other_admin_user.phone_number])
        self.assertTrue(shown[self.salesperson.user.phone_number])

    def test_a_superuser_sees_every_qr_in_the_list(self):
        """tests/test_rotate_qr.py::RotateQrTest::test_a_superuser_sees_every_qr_in_the_list"""
        shown = self._list_totp(self.superuser)

        self.assertTrue(shown[self.other_admin_user.phone_number])
        self.assertTrue(shown[self.salesperson.user.phone_number])

    def test_a_superuser_may_rotate_an_admins_fallback_profile(self):
        """tests/test_rotate_qr.py::RotateQrTest::test_a_superuser_may_rotate_an_admins_fallback_profile"""
        fallback = self.other_admin_user.salesperson_profile
        self.login_as(self.superuser)

        response = self.client.post(SALESPERSON_URL.format(id=fallback.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)


class AdminSiteRulesTest(WebApiTestCase):
    """Only a superuser sees or deletes another admin in the Django admin site.

    tests/test_rotate_qr.py::AdminSiteRulesTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.first_user = _make_user("7777777771", "first", cls.superuser)
        cls.first = Admin.objects.create(user=cls.first_user, created_by=cls.superuser)
        cls.second_user = _make_user("7777777772", "second", cls.superuser)
        cls.second = Admin.objects.create(user=cls.second_user, created_by=cls.superuser)

    def _request(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return request

    def _titles(self, viewer, target):
        admin_site = site._registry[User]
        fieldsets = admin_site.get_fieldsets(self._request(viewer), target)
        return [title for title, _ in fieldsets]

    def test_an_admin_does_not_see_another_admins_qr(self):
        """tests/test_rotate_qr.py::AdminSiteRulesTest::test_an_admin_does_not_see_another_admins_qr"""
        self.assertNotIn(
            "Authenticator app (TOTP)", self._titles(self.first_user, self.second_user)
        )

    def test_an_admin_still_sees_their_own_qr(self):
        """tests/test_rotate_qr.py::AdminSiteRulesTest::test_an_admin_still_sees_their_own_qr"""
        self.assertIn("Authenticator app (TOTP)", self._titles(self.first_user, self.first_user))

    def test_a_superuser_sees_an_admins_qr(self):
        """tests/test_rotate_qr.py::AdminSiteRulesTest::test_a_superuser_sees_an_admins_qr"""
        self.assertIn("Authenticator app (TOTP)", self._titles(self.superuser, self.second_user))

    def test_only_a_superuser_may_delete_an_admin(self):
        """tests/test_rotate_qr.py::AdminSiteRulesTest::test_only_a_superuser_may_delete_an_admin"""
        profile_admin = site._registry[Admin]
        self.assertFalse(
            profile_admin.has_delete_permission(self._request(self.first_user), self.second)
        )
        self.assertFalse(
            profile_admin.has_change_permission(self._request(self.first_user), self.second)
        )
        self.assertTrue(
            profile_admin.has_delete_permission(self._request(self.superuser), self.second)
        )
