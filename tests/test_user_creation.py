"""ORM-backed tests for the admin / salesperson creation endpoints.

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``) and add
their own geography + profiles in ``setUpTestData``. Request/response flows are
exercised over the test :class:`~rest_framework.test.APIClient` with a logged-in
session, since these are session-only web endpoints.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Country, State
from authentication.models import Admin, SalesPerson
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class UserCreationTest(WebApiTestCase):
    """Cover permission gating, creation and payload shape for admin/salesperson.

    tests/test_user_creation.py::UserCreationTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build the geography tree, an app admin, a plain user and a salesperson."""
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
        Admin.objects.create(
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

    # -- permission gating ----------------------------------------------------

    def test_anonymous_requests_are_rejected(self):
        """tests/test_user_creation.py::UserCreationTest::test_anonymous_requests_are_rejected"""
        for path in ("/api/sales-admin/admins", "/api/sales-admin/sales-people"):
            self.assertIn(
                self.client.post(path, {"name": "x"}, format="json").status_code,
                (401, 403),
            )
            self.assertIn(self.client.get(path).status_code, (401, 403))

    def test_only_superuser_can_create_admin(self):
        """tests/test_user_creation.py::UserCreationTest::test_only_superuser_can_create_admin"""
        payload = {
            "name": "Should Not Exist",
            "phone_number": "9000000099",
            "city": self.city.id,
        }
        for user in (self.plain, self.seed_admin, self.salesperson.user):
            self.login_as(user)
            self.assertEqual(
                self.client.post("/api/sales-admin/admins", payload, format="json").status_code,
                status.HTTP_403_FORBIDDEN,
            )

        self.login_as(self.superuser)
        self.assertEqual(
            self.client.post("/api/sales-admin/admins", payload, format="json").status_code,
            status.HTTP_201_CREATED,
        )

    def test_only_admin_can_create_salesperson(self):
        """tests/test_user_creation.py::UserCreationTest::test_only_admin_can_create_salesperson"""
        payload = {
            "name": "Blocked Person",
            "phone_number": "9000000088",
            "city": self.city.id,
        }
        # A plain user and a salesperson are both forbidden.
        for user in (self.plain, self.salesperson.user):
            self.login_as(user)
            status_code = self.client.post(
                "/api/sales-admin/sales-people", payload, format="json"
            ).status_code
            self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        # A superuser only creates admins -> also forbidden for sales-people.
        self.login_as(self.superuser)
        self.assertEqual(
            self.client.post("/api/sales-admin/sales-people", payload, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )

        # An application admin may create a salesperson.
        self.login_as(self.seed_admin)
        self.assertEqual(
            self.client.post("/api/sales-admin/sales-people", payload, format="json").status_code,
            status.HTTP_201_CREATED,
        )

    # -- admin creation -------------------------------------------------------

    def test_create_admin_creates_fallback_salesperson_and_payload_shape(self):
        """tests/test_user_creation.py::UserCreationTest::test_create_admin_creates_fallback_salesperson_and_payload_shape"""
        self.login_as(self.superuser)
        response = self.client.post(
            "/api/sales-admin/admins",
            {
                "name": "Vikram Kumar",
                "email": "vikram@example.com",
                "phone_number": "9000000001",
                "can_update_stock_count": True,
                "city": self.city.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        admin = response.data

        self.assertEqual(admin["name"], "Vikram Kumar")
        self.assertEqual(admin["email"], "vikram@example.com")
        self.assertEqual(admin["phone_number"], "9000000001")
        self.assertEqual(admin["role"], "admin")
        self.assertTrue(admin["can_update_stock_count"])
        # Admin payload must not leak internal / address / city keys.
        for key in ("user_id", "city", "address", "is_deleted", "deleted_by"):
            self.assertNotIn(key, admin)

        # The fallback salesperson row exists for the same account.
        created_user = User.objects.get(phone_number="9000000001")
        self.assertEqual(SalesPerson.objects.get(user=created_user).city_id, self.city.id)

    def test_create_admin_duplicate_phone_rejected(self):
        """tests/test_user_creation.py::UserCreationTest::test_create_admin_duplicate_phone_rejected"""
        self.login_as(self.superuser)
        payload = {
            "name": "Duplicate",
            "phone_number": "9000000002",
            "city": self.city.id,
        }
        self.assertEqual(
            self.client.post("/api/sales-admin/admins", payload, format="json").status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            self.client.post("/api/sales-admin/admins", payload, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_admin_invalid_payload_rejected(self):
        """tests/test_user_creation.py::UserCreationTest::test_create_admin_invalid_payload_rejected"""
        self.login_as(self.superuser)
        for payload in (
            {"name": "No Phone", "city": self.city.id},
            {"name": "Bad Phone", "phone_number": "12345", "city": self.city.id},
            {"name": "No City", "phone_number": "9000000003"},
        ):
            self.assertEqual(
                self.client.post("/api/sales-admin/admins", payload, format="json").status_code,
                status.HTTP_400_BAD_REQUEST,
                payload,
            )

    def test_list_admins_excludes_deleted(self):
        """tests/test_user_creation.py::UserCreationTest::test_list_admins_excludes_deleted"""
        self.login_as(self.superuser)
        created = self.client.post(
            "/api/sales-admin/admins",
            {"name": "Vikram Kumar", "phone_number": "9000000050", "city": self.city.id},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        # Soft-delete the seed admin; it must disappear from the list.
        Admin.objects.get(user=self.seed_admin).delete(deleted_by=self.superuser)

        response = self.client.get("/api/sales-admin/admins")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        admins = response.data
        self.assertTrue(any(item["name"] == "Vikram Kumar" for item in admins))
        self.assertFalse(any(item.get("name") == "seed admin" for item in admins))
        for item in admins:
            self.assertEqual(item["role"], "admin")
            for key in ("user_id", "city", "address", "is_deleted", "deleted_by"):
                self.assertNotIn(key, item)

    def test_list_admins_includes_totp_uri(self):
        """The list endpoint returns each admin's TOTP provisioning URI, not just creation.

        tests/test_user_creation.py::UserCreationTest::test_list_admins_includes_totp_uri
        """
        self.login_as(self.superuser)
        created = self.client.post(
            "/api/sales-admin/admins",
            {"name": "Vikram Kumar", "phone_number": "9000000060", "city": self.city.id},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        response = self.client.get("/api/sales-admin/admins")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        vikram = next(item for item in response.data if item["name"] == "Vikram Kumar")
        self.assertTrue(vikram["totp"]["provisioning_uri"])

    # -- salesperson creation ------------------------------------------------

    def test_create_salesperson_payload_shape(self):
        """tests/test_user_creation.py::UserCreationTest::test_create_salesperson_payload_shape"""
        self.login_as(self.seed_admin)
        response = self.client.post(
            "/api/sales-admin/sales-people",
            {
                "name": "Ramesh Patil",
                "phone_number": "9000000011",
                "city": self.city.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        person = response.data
        self.assertEqual(person["name"], "Ramesh Patil")
        self.assertIsNone(person["email"])
        self.assertEqual(person["phone_number"], "9000000011")
        self.assertEqual(person["role"], "salesperson")
        self.assertEqual(person["city"]["id"], self.city.id)
        for key in ("user_id", "address", "is_deleted", "deleted_by"):
            self.assertNotIn(key, person)

    def test_list_sales_people_excludes_deleted(self):
        """tests/test_user_creation.py::UserCreationTest::test_list_sales_people_excludes_deleted"""
        self.login_as(self.seed_admin)
        created = self.client.post(
            "/api/sales-admin/sales-people",
            {"name": "Ramesh Patil", "phone_number": "9000000051", "city": self.city.id},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        self.salesperson.delete(deleted_by=self.superuser)

        response = self.client.get("/api/sales-admin/sales-people")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        people = response.data
        self.assertTrue(any(item["name"] == "Ramesh Patil" for item in people))
        self.assertFalse(any(item.get("name") == "seed salesperson" for item in people))
        for item in people:
            self.assertEqual(item["role"], "salesperson")
            self.assertIn("city", item)
            for key in ("user_id", "address", "is_deleted", "deleted_by"):
                self.assertNotIn(key, item)

    def test_list_sales_people_includes_totp_uri(self):
        """The list endpoint returns each sales person's TOTP provisioning URI.

        tests/test_user_creation.py::UserCreationTest::test_list_sales_people_includes_totp_uri
        """
        self.login_as(self.seed_admin)
        created = self.client.post(
            "/api/sales-admin/sales-people",
            {"name": "Ramesh Patil", "phone_number": "9000000061", "city": self.city.id},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        response = self.client.get("/api/sales-admin/sales-people")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ramesh = next(item for item in response.data if item["name"] == "Ramesh Patil")
        self.assertTrue(ramesh["totp"]["provisioning_uri"])
