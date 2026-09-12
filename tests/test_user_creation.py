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
        """Build the geography tree, an app admin and a salesperson."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        Admin.objects.create(
            user=cls.superuser, can_update_stock_count=False, created_by=cls.superuser
        )

        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.superuser}
        )
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

    def test_invalid_admin_creation_payloads_are_rejected(self):
        """tests/test_user_creation.py::UserCreationTest::test_invalid_admin_creation_payloads_are_rejected"""
        self.login_as(self.superuser)

        # Taking a phone number twice is only a duplicate the second time round.
        taken = {"name": "Duplicate", "phone_number": "9000000002", "city": self.city.id}
        self.assertEqual(
            self.client.post("/api/sales-admin/admins", taken, format="json").status_code,
            status.HTTP_201_CREATED,
        )

        cases = [
            ("duplicate phone", taken),
            ("missing phone", {"name": "No Phone", "city": self.city.id}),
            (
                "malformed phone",
                {"name": "Bad Phone", "phone_number": "12345", "city": self.city.id},
            ),
            ("missing city", {"name": "No City", "phone_number": "9000000003"}),
        ]
        for label, payload in cases:
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.post(
                        "/api/sales-admin/admins", payload, format="json"
                    ).status_code,
                    status.HTTP_400_BAD_REQUEST,
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

        # The list carries each admin's TOTP provisioning URI, not just creation.
        vikram = next(item for item in admins if item["name"] == "Vikram Kumar")
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

        ramesh = next(item for item in people if item["name"] == "Ramesh Patil")
        self.assertTrue(ramesh["totp"]["provisioning_uri"])

