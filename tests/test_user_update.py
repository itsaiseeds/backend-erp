"""ORM-backed tests for the admin / salesperson update endpoints.

These use the ``DMLTestCase`` baseline (superuser phone ``9999999999``) and add
their own geography + profiles in ``setUpTestData``. Update flows are exercised
over the test :class:`~rest_framework.test.APIClient` with explicit bearer
``Token`` credentials.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator.models import City, Country, State
from authentication.models import Admin, SalesPerson
from tests.common import DMLTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class UserUpdateTest(DMLTestCase):
    """Cover permission gating, field updates and payload shape for admin/salesperson.

    tests/test_user_update.py::UserUpdateTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build the geography tree, an app admin and a salesperson."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        cls.country = Country.objects.create(name="India", iso_code="IN", created_by=cls.superuser)
        cls.state = State.objects.create(
            name="Maharashtra", code="MH", country=cls.country, created_by=cls.superuser
        )
        cls.city = City.objects.create(name="Pune", state=cls.state, created_by=cls.superuser)
        cls.city_2 = City.objects.create(name="Mumbai", state=cls.state, created_by=cls.superuser)

        cls.seed_admin = User.objects.create_user(
            phone_number="7777777777",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        cls.admin = Admin.objects.create(
            user=cls.seed_admin, can_update_stock_count=True, created_by=cls.superuser
        )

        cls.plain = User.objects.create_user(
            phone_number="6666666666",
            name="plain user",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )

        cls.salesperson = SalesPerson.objects.create(
            user=User.objects.create_user(
                phone_number="5555555555",
                name="seed salesperson",
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            ),
            city=cls.city,
            created_by=cls.superuser,
        )

    def setUp(self):
        """Create an unauthenticated API client for every test in this class."""
        self.client = APIClient()

    def _auth_as(self, user) -> None:
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")  # type: ignore[attr-defined]

    def _clear_auth(self) -> None:
        self.client.credentials()  # type: ignore[attr-defined]

    # -- permission gating (admin) ------------------------------------------

    def test_anonymous_admin_update_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_anonymous_admin_update_rejected"""
        self._clear_auth()
        response = self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}", {"name": "x"}, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_only_superuser_can_update_admin(self):
        """tests/test_user_update.py::UserUpdateTest::test_only_superuser_can_update_admin"""
        url = f"/api/sales_admin/admins/{self.admin.id}"
        for user in (self.plain, self.seed_admin, self.salesperson.user):
            self._auth_as(user)
            self.assertEqual(
                self.client.patch(url, {"name": "x"}, format="json").status_code,
                status.HTTP_403_FORBIDDEN,
            )

        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.patch(url, {"name": "Updated"}, format="json").status_code,
            status.HTTP_200_OK,
        )

    def test_update_admin_not_found(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_not_found"""
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.patch(
                "/api/sales_admin/admins/999999", {"name": "x"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_update_soft_deleted_admin_not_found(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_soft_deleted_admin_not_found"""
        self._auth_as(self.superuser)
        self.admin.delete(deleted_by=self.superuser)
        self.assertEqual(
            self.client.patch(
                f"/api/sales_admin/admins/{self.admin.id}", {"name": "x"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # -- admin field updates -------------------------------------------------

    def test_update_admin_name(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_name"""
        self._auth_as(self.superuser)
        response = self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}",
            {"name": "Updated Admin"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["name"], "Updated Admin")
        self.seed_admin.refresh_from_db()
        self.assertEqual(self.seed_admin.name, "Updated Admin")

    def test_update_admin_email(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_email"""
        self._auth_as(self.superuser)
        response = self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}",
            {"email": "updated@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["email"], "updated@example.com")
        self.seed_admin.refresh_from_db()
        self.assertEqual(self.seed_admin.email, "updated@example.com")

    def test_update_admin_can_update_stock_count(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_can_update_stock_count"""
        self._auth_as(self.superuser)
        self.assertEqual(self.admin.can_update_stock_count, True)
        response = self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}",
            {"can_update_stock_count": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertFalse(response.data["can_update_stock_count"])
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.can_update_stock_count)

    def test_update_admin_multiple_fields(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_multiple_fields"""
        self._auth_as(self.superuser)
        response = self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}",
            {"name": "Bulk Updated", "email": "bulk@example.com", "can_update_stock_count": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["name"], "Bulk Updated")
        self.assertEqual(response.data["email"], "bulk@example.com")
        self.assertFalse(response.data["can_update_stock_count"])
        self.seed_admin.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual(self.seed_admin.name, "Bulk Updated")
        self.assertEqual(self.seed_admin.email, "bulk@example.com")
        self.assertFalse(self.admin.can_update_stock_count)

    def test_update_admin_partial_body_leaves_others_unchanged(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_partial_body_leaves_others_unchanged"""
        self._auth_as(self.superuser)
        self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}", {"name": "Only Name"}, format="json"
        )
        self.seed_admin.refresh_from_db()
        self.assertEqual(self.seed_admin.name, "Only Name")
        self.assertIsNone(self.seed_admin.email)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.can_update_stock_count)

    def test_update_admin_empty_body_returns_unchanged(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_empty_body_returns_unchanged"""
        self._auth_as(self.superuser)
        response = self.client.patch(f"/api/sales_admin/admins/{self.admin.id}", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["name"], "seed admin")

    def test_update_admin_invalid_email_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_invalid_email_rejected"""
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.patch(
                f"/api/sales_admin/admins/{self.admin.id}",
                {"email": "not-an-email"},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_admin_phone_number(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_phone_number"""
        self._auth_as(self.superuser)
        response = self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}",
            {"phone_number": "9999999998"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["phone_number"], "9999999998")
        self.seed_admin.refresh_from_db()
        self.assertEqual(self.seed_admin.phone_number, "9999999998")

    def test_update_admin_invalid_phone_number_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_invalid_phone_number_rejected"""
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.patch(
                f"/api/sales_admin/admins/{self.admin.id}",
                {"phone_number": "12345"},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_admin_duplicate_phone_number_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_duplicate_phone_number_rejected"""
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.patch(
                f"/api/sales_admin/admins/{self.admin.id}",
                {"phone_number": "5555555555"},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_admin_with_own_phone_number_is_allowed(self):
        """PATCHing an admin with the phone they already have must succeed.

        Regression: the uniqueness check previously matched the row being
        edited itself, so an unchanged phone_number in the payload 400'd.

        tests/test_user_update.py::UserUpdateTest::test_update_admin_with_own_phone_number_is_allowed
        """
        self._auth_as(self.superuser)
        response = self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}",
            {"phone_number": self.seed_admin.phone_number, "name": "Same Phone"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.seed_admin.refresh_from_db()
        self.assertEqual(self.seed_admin.name, "Same Phone")

    def test_update_admin_payload_shape(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_admin_payload_shape"""
        self._auth_as(self.superuser)
        response = self.client.patch(
            f"/api/sales_admin/admins/{self.admin.id}",
            {"name": "Payload Check"},
            format="json",
        )
        admin = response.data
        self.assertEqual(admin["role"], "admin")
        self.assertEqual(admin["id"], self.admin.id)
        self.assertIn("created_by", admin)
        self.assertIn("created_at", admin)
        self.assertIn("can_update_stock_count", admin)
        for key in ("user_id", "city", "address", "is_deleted", "deleted_by", "totp"):
            self.assertNotIn(key, admin)

    # -- permission gating (salesperson) -------------------------------------

    def test_anonymous_salesperson_update_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_anonymous_salesperson_update_rejected"""
        self._clear_auth()
        response = self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {"name": "x"},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_only_admin_can_update_salesperson(self):
        """tests/test_user_update.py::UserUpdateTest::test_only_admin_can_update_salesperson"""
        url = f"/api/sales_admin/sales-people/{self.salesperson.id}"
        # A plain user and a salesperson are both forbidden.
        for user in (self.plain, self.salesperson.user):
            self._auth_as(user)
            self.assertEqual(
                self.client.patch(url, {"name": "x"}, format="json").status_code,
                status.HTTP_403_FORBIDDEN,
            )
        # A superuser only manages admins -> also forbidden here.
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.patch(url, {"name": "x"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        # An application admin may update a salesperson.
        self._auth_as(self.seed_admin)
        self.assertEqual(
            self.client.patch(url, {"name": "Updated"}, format="json").status_code,
            status.HTTP_200_OK,
        )

    def test_update_salesperson_not_found(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_not_found"""
        self._auth_as(self.seed_admin)
        self.assertEqual(
            self.client.patch(
                "/api/sales_admin/sales-people/999999", {"name": "x"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_update_soft_deleted_salesperson_not_found(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_soft_deleted_salesperson_not_found"""
        self._auth_as(self.seed_admin)
        self.salesperson.delete(deleted_by=self.superuser)
        self.assertEqual(
            self.client.patch(
                f"/api/sales_admin/sales-people/{self.salesperson.id}",
                {"name": "x"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # -- salesperson field updates -------------------------------------------

    def test_update_salesperson_name(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_name"""
        self._auth_as(self.seed_admin)
        response = self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {"name": "Updated Person"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["name"], "Updated Person")
        self.salesperson.user.refresh_from_db()
        self.assertEqual(self.salesperson.user.name, "Updated Person")

    def test_update_salesperson_email(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_email"""
        self._auth_as(self.seed_admin)
        response = self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {"email": "person@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["email"], "person@example.com")
        self.salesperson.user.refresh_from_db()
        self.assertEqual(self.salesperson.user.email, "person@example.com")

    def test_update_salesperson_city(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_city"""
        self._auth_as(self.seed_admin)
        response = self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {"city": self.city_2.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["city"]["id"], self.city_2.id)
        self.salesperson.refresh_from_db()
        self.assertEqual(self.salesperson.city_id, self.city_2.id)

    def test_update_salesperson_multiple_fields(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_multiple_fields"""
        self._auth_as(self.seed_admin)
        response = self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {"name": "Bulk Person", "email": "bulk@example.com", "city": self.city_2.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["name"], "Bulk Person")
        self.assertEqual(response.data["email"], "bulk@example.com")
        self.assertEqual(response.data["city"]["id"], self.city_2.id)
        self.salesperson.user.refresh_from_db()
        self.salesperson.refresh_from_db()
        self.assertEqual(self.salesperson.user.name, "Bulk Person")
        self.assertEqual(self.salesperson.user.email, "bulk@example.com")
        self.assertEqual(self.salesperson.city_id, self.city_2.id)

    def test_update_salesperson_partial_body_leaves_others_unchanged(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_partial_body_leaves_others_unchanged"""
        self._auth_as(self.seed_admin)
        self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {"name": "Only Person"},
            format="json",
        )
        self.salesperson.user.refresh_from_db()
        self.assertEqual(self.salesperson.user.name, "Only Person")
        self.assertIsNone(self.salesperson.user.email)
        self.salesperson.refresh_from_db()
        self.assertEqual(self.salesperson.city_id, self.city.id)

    def test_update_salesperson_invalid_city_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_invalid_city_rejected"""
        self._auth_as(self.seed_admin)
        self.assertEqual(
            self.client.patch(
                f"/api/sales_admin/sales-people/{self.salesperson.id}",
                {"city": 999999},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_salesperson_phone_number(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_phone_number"""
        self._auth_as(self.seed_admin)
        response = self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {"phone_number": "9999999990"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["phone_number"], "9999999990")
        self.salesperson.user.refresh_from_db()
        self.assertEqual(self.salesperson.user.phone_number, "9999999990")

    def test_update_salesperson_invalid_phone_number_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_invalid_phone_number_rejected"""
        self._auth_as(self.seed_admin)
        self.assertEqual(
            self.client.patch(
                f"/api/sales_admin/sales-people/{self.salesperson.id}",
                {"phone_number": "12345"},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_salesperson_duplicate_phone_number_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_duplicate_phone_number_rejected"""
        self._auth_as(self.seed_admin)
        self.assertEqual(
            self.client.patch(
                f"/api/sales_admin/sales-people/{self.salesperson.id}",
                {"phone_number": "7777777777"},
                format="json",
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_update_salesperson_with_own_phone_number_is_allowed(self):
        """Same regression as for admins: unchanged own phone must not 400.

        tests/test_user_update.py::UserUpdateTest::test_update_salesperson_with_own_phone_number_is_allowed
        """
        self._auth_as(self.seed_admin)
        response = self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {
                "phone_number": self.salesperson.user.phone_number,
                "name": "Same Phone Person",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.salesperson.user.refresh_from_db()
        self.assertEqual(self.salesperson.user.name, "Same Phone Person")

    def test_update_salesperson_payload_shape(self):
        """tests/test_user_update.py::UserUpdateTest::test_update_salesperson_payload_shape"""
        self._auth_as(self.seed_admin)
        response = self.client.patch(
            f"/api/sales_admin/sales-people/{self.salesperson.id}",
            {"name": "Payload Person"},
            format="json",
        )
        person = response.data
        self.assertEqual(person["role"], "salesperson")
        self.assertEqual(person["id"], self.salesperson.id)
        self.assertIn("city", person)
        for key in ("user_id", "address", "is_deleted", "deleted_by", "totp"):
            self.assertNotIn(key, person)


class UserDeleteTest(DMLTestCase):
    """Cover delete permission gating and soft-delete behaviour for admin/salesperson.

    tests/test_user_update.py::UserDeleteTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build the geography tree, an app admin and a salesperson."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        cls.country = Country.objects.create(name="India", iso_code="IN", created_by=cls.superuser)
        cls.state = State.objects.create(
            name="Maharashtra", code="MH", country=cls.country, created_by=cls.superuser
        )
        cls.city = City.objects.create(name="Pune", state=cls.state, created_by=cls.superuser)

        cls.seed_admin = User.objects.create_user(
            phone_number="7777777777",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        # Mirror the API create-admin flow, which grants the admin the
        # permission required to soft-delete sales people.
        cls.seed_admin.user_permissions.add(
            Permission.objects.get(codename="delete_salesperson")
        )
        cls.admin = Admin.objects.create(
            user=cls.seed_admin, can_update_stock_count=True, created_by=cls.superuser
        )

        cls.plain = User.objects.create_user(
            phone_number="6666666666",
            name="plain user",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )

        cls.salesperson = SalesPerson.objects.create(
            user=User.objects.create_user(
                phone_number="5555555555",
                name="seed salesperson",
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            ),
            city=cls.city,
            created_by=cls.superuser,
        )

    def setUp(self):
        """Create an unauthenticated API client for every test in this class."""
        self.client = APIClient()

    def _auth_as(self, user) -> None:
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")  # type: ignore[attr-defined]

    def _clear_auth(self) -> None:
        self.client.credentials()  # type: ignore[attr-defined]

    # -- permission gating (admin delete) -----------------------------------

    def test_anonymous_admin_delete_rejected(self):
        """tests/test_user_update.py::UserDeleteTest::test_anonymous_admin_delete_rejected"""
        self._clear_auth()
        response = self.client.delete(f"/api/sales_admin/admins/{self.admin.id}")
        self.assertIn(response.status_code, (401, 403))

    def test_only_superuser_can_delete_admin(self):
        """tests/test_user_update.py::UserDeleteTest::test_only_superuser_can_delete_admin"""
        url = f"/api/sales_admin/admins/{self.admin.id}"
        # A plain user, an app admin and a salesperson are all forbidden.
        for user in (self.plain, self.seed_admin, self.salesperson.user):
            self._auth_as(user)
            self.assertEqual(
                self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN
            )

        # A superuser may delete an admin.
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT
        )

    def test_delete_admin_not_found(self):
        """tests/test_user_update.py::UserDeleteTest::test_delete_admin_not_found"""
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.delete("/api/sales_admin/admins/999999").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_admin_soft_deletes_row(self):
        """tests/test_user_update.py::UserDeleteTest::test_delete_admin_soft_deletes_row"""
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.delete(f"/api/sales_admin/admins/{self.admin.id}").status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_deleted)
        self.assertIsNotNone(self.admin.deleted_at)
        self.assertEqual(self.admin.deleted_by_id, self.superuser.id)

    def test_delete_soft_deleted_admin_not_found(self):
        """tests/test_user_update.py::UserDeleteTest::test_delete_soft_deleted_admin_not_found"""
        self._auth_as(self.superuser)
        self.admin.delete(deleted_by=self.superuser)
        self.assertEqual(
            self.client.delete(f"/api/sales_admin/admins/{self.admin.id}").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # -- permission gating (salesperson delete) -----------------------------

    def test_anonymous_salesperson_delete_rejected(self):
        """tests/test_user_update.py::UserDeleteTest::test_anonymous_salesperson_delete_rejected"""
        self._clear_auth()
        response = self.client.delete(
            f"/api/sales_admin/sales-people/{self.salesperson.id}"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_admin_can_delete_salesperson(self):
        """tests/test_user_update.py::UserDeleteTest::test_admin_can_delete_salesperson"""
        self._auth_as(self.seed_admin)
        self.assertEqual(
            self.client.delete(
                f"/api/sales_admin/sales-people/{self.salesperson.id}"
            ).status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_superuser_can_delete_salesperson(self):
        """tests/test_user_update.py::UserDeleteTest::test_superuser_can_delete_salesperson"""
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.delete(
                f"/api/sales_admin/sales-people/{self.salesperson.id}"
            ).status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def test_plain_and_salesperson_cannot_delete_salesperson(self):
        """tests/test_user_update.py::UserDeleteTest::test_plain_and_salesperson_cannot_delete_salesperson"""
        url = f"/api/sales_admin/sales-people/{self.salesperson.id}"
        for user in (self.plain, self.salesperson.user):
            self._auth_as(user)
            self.assertEqual(
                self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN
            )

    def test_delete_salesperson_not_found(self):
        """tests/test_user_update.py::UserDeleteTest::test_delete_salesperson_not_found"""
        self._auth_as(self.superuser)
        self.assertEqual(
            self.client.delete("/api/sales_admin/sales-people/999999").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_salesperson_soft_deletes_row(self):
        """tests/test_user_update.py::UserDeleteTest::test_delete_salesperson_soft_deletes_row"""
        self._auth_as(self.seed_admin)
        self.assertEqual(
            self.client.delete(
                f"/api/sales_admin/sales-people/{self.salesperson.id}"
            ).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.salesperson.refresh_from_db()
        self.assertTrue(self.salesperson.is_deleted)
        self.assertIsNotNone(self.salesperson.deleted_at)
        self.assertEqual(self.salesperson.deleted_by_id, self.seed_admin.id)

    def test_delete_soft_deleted_salesperson_not_found(self):
        """tests/test_user_update.py::UserDeleteTest::test_delete_soft_deleted_salesperson_not_found"""
        self._auth_as(self.superuser)
        self.salesperson.delete(deleted_by=self.superuser)
        self.assertEqual(
            self.client.delete(
                f"/api/sales_admin/sales-people/{self.salesperson.id}"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
