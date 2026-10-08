"""ORM-backed tests for the sales-admin godown-manager endpoints.

Role gating (``admin_required``) is owned by ``tests/test_view_contracts.py``.
These cover what the endpoints do: creating, listing, updating and deleting a
godown manager, and the rule that an admin's own profile is superuser-only.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token

from authentication.models import Admin, GodownManager, LabTester
from tests.common import WebApiTestCase

User = get_user_model()

LIST_URL = "/api/sales-admin/godown-managers"
ITEM_URL = "/api/sales-admin/godown-managers/{id}"


class GodownManagerApiTest(WebApiTestCase):
    """tests/test_godown_manager_api.py::GodownManagerApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        cls.seed_admin = User.objects.create_user(
            phone_number="7777777777",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.seed_admin, created_by=cls.superuser)

    def _create(self, phone: str = "9000000011", **extra):
        body = {"name": "Mohan Lal", "phone_number": phone, **extra}
        return self.client.post(LIST_URL, body, format="json")

    def test_create_list_update_and_delete_round_trip(self):
        """tests/test_godown_manager_api.py::GodownManagerApiTest::test_create_list_update_and_delete_round_trip"""
        self.login_as(self.seed_admin)

        created = self._create()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        manager = created.data
        self.assertEqual(manager["role"], "godown_manager")
        self.assertEqual(manager["phone_number"], "9000000011")
        self.assertTrue(manager["totp"]["provisioning_uri"])
        for key in ("city", "user_id", "is_deleted", "deleted_by"):
            self.assertNotIn(key, manager)

        listed = self.client.get(LIST_URL)
        self.assertIn(manager["id"], [row["id"] for row in listed.data])

        patched = self.client.patch(
            ITEM_URL.format(id=manager["id"]), {"name": "Mohan L."}, format="json"
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.content)
        self.assertEqual(patched.data["name"], "Mohan L.")

        token = Token.objects.create(user=GodownManager.objects.get(id=manager["id"]).user)
        deleted = self.client.delete(ITEM_URL.format(id=manager["id"]))
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(manager["id"], [row["id"] for row in self.client.get(LIST_URL).data])
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    def test_a_duplicate_phone_number_is_400(self):
        """tests/test_godown_manager_api.py::GodownManagerApiTest::test_a_duplicate_phone_number_is_400"""
        self.login_as(self.seed_admin)
        self.assertEqual(self._create().status_code, status.HTTP_201_CREATED)
        duplicate = self._create()
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already a godown manager", str(duplicate.data))

    def test_an_admins_own_godown_profile_is_superuser_only(self):
        """tests/test_godown_manager_api.py::GodownManagerApiTest::test_an_admins_own_godown_profile_is_superuser_only"""
        profile = GodownManager.objects.create(user=self.seed_admin, created_by=self.superuser)
        other_admin = User.objects.create_user(
            phone_number="7777777776",
            name="other admin",
            is_verified=True,
            created_by=self.superuser,
            verified_by=self.superuser,
        )
        Admin.objects.create(user=other_admin, created_by=self.superuser)

        self.login_as(other_admin)
        url = ITEM_URL.format(id=profile.id)
        self.assertEqual(
            self.client.patch(url, {"name": "x"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)

    def test_deleting_the_only_role_deactivates_the_user_and_recreating_revives_it(self):
        """tests/test_godown_manager_api.py::GodownManagerApiTest::test_deleting_the_only_role_deactivates_the_user_and_recreating_revives_it"""
        self.login_as(self.seed_admin)
        first = self._create()
        user = User.objects.get(phone_number="9000000011")
        old_secret = user.totp_secret

        self.client.delete(ITEM_URL.format(id=first.data["id"]))
        user.refresh_from_db()
        self.assertFalse(user.is_active)

        again = self._create(name="Renamed")
        self.assertEqual(again.status_code, status.HTTP_201_CREATED, again.content)
        self.assertEqual(again.data["id"], first.data["id"])
        self.assertEqual(User.objects.filter(phone_number="9000000011").count(), 1)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertNotEqual(user.totp_secret, old_secret)
        self.assertEqual(GodownManager.objects.get(user=user).created_by, self.seed_admin)

    def test_deleting_one_of_several_roles_keeps_the_user_active(self):
        """tests/test_godown_manager_api.py::GodownManagerApiTest::test_deleting_one_of_several_roles_keeps_the_user_active"""
        self.login_as(self.seed_admin)
        created = self._create()
        user = User.objects.get(phone_number="9000000011")
        LabTester.objects.create(user=user, created_by=self.seed_admin)

        self.client.delete(ITEM_URL.format(id=created.data["id"]))
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_lab_tester)
        self.assertFalse(user.is_godown_manager)

    def test_adding_a_role_to_an_existing_user_reuses_the_account(self):
        """tests/test_godown_manager_api.py::GodownManagerApiTest::test_adding_a_role_to_an_existing_user_reuses_the_account"""
        self.login_as(self.seed_admin)
        tester = self.client.post(
            "/api/sales-admin/lab-testers",
            {"name": "Asha", "phone_number": "9000000012"},
            format="json",
        )
        self.assertEqual(tester.status_code, status.HTTP_201_CREATED, tester.content)

        manager = self._create(phone="9000000012")
        self.assertEqual(manager.status_code, status.HTTP_201_CREATED, manager.content)
        user = User.objects.get(phone_number="9000000012")
        self.assertTrue(user.is_lab_tester and user.is_godown_manager)

    def test_only_a_superuser_may_add_a_role_to_an_admin(self):
        """tests/test_godown_manager_api.py::GodownManagerApiTest::test_only_a_superuser_may_add_a_role_to_an_admin"""
        other = User.objects.create_user(
            phone_number="7777777776",
            name="other admin",
            is_verified=True,
            created_by=self.superuser,
            verified_by=self.superuser,
        )
        Admin.objects.create(user=other, created_by=self.superuser)

        self.login_as(self.seed_admin)
        self.assertEqual(
            self._create(phone="7777777776").status_code, status.HTTP_403_FORBIDDEN
        )
        Admin.objects.create(user=self.superuser, created_by=self.superuser)
        self.login_as(self.superuser)
        self.assertEqual(
            self._create(phone="7777777776").status_code, status.HTTP_201_CREATED
        )
