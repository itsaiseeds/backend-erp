"""ORM-backed tests for the non-stock inward endpoints (list/create + patch + delete).

Uses the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and adds its own users in ``setUpTestData``: a stock admin (holds
``can_update_stock_count``), a plain admin (does not) and a verified user with no
admin profile. ``dml.sql`` seeds three entries, cleared here so each test starts
from an empty register.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import NonStockInward
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

ENTRIES_URL = "/api/sales-admin/non-stock-inwards"
ENTRY_URL = "/api/sales-admin/non-stock-inward"


class NonStockInwardApiTest(WebApiTestCase):
    """A standalone register: any admin reads it, only stock admins write it.

    tests/test_non_stock_inward_api.py::NonStockInwardApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build a stock admin, a plain admin and a non-admin user."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        def user(phone, name):
            return User.objects.create_user(
                phone_number=phone,
                name=name,
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            )

        cls.stock_admin = user("7777777771", "stock admin")
        Admin.objects.create(
            user=cls.stock_admin, can_update_stock_count=True, created_by=cls.superuser
        )
        cls.plain_admin = user("7777777772", "plain admin")
        Admin.objects.create(
            user=cls.plain_admin, can_update_stock_count=False, created_by=cls.superuser
        )
        cls.nobody = user("7777777773", "no role")
        NonStockInward.all_objects.all().delete()

    # -- helpers --------------------------------------------------------------

    def _create(self, **overrides):
        """POST an entry and return the response (defaults: 5 litre of a pesticide)."""
        body = {
            "name": "Imidacloprid",
            "description": "Store spray",
            "company_name": "Bayer",
            "price": "1850.50",
            "quantity": "5",
            "unit": "litre",
            **overrides,
        }
        return self.client.post(ENTRIES_URL, body, format="json")

    def _url(self, public_id):
        return f"{ENTRY_URL}/{public_id}"

    # -- create + list ----------------------------------------------------------

    def test_create_echoes_the_entry_and_it_is_listed(self):
        """tests/test_non_stock_inward_api.py::NonStockInwardApiTest::test_create_echoes_the_entry_and_it_is_listed"""
        self.login_as(self.stock_admin)
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        entry = response.data
        self.assertTrue(entry["public_id"].startswith("NS-"))
        self.assertEqual(
            {k: v for k, v in entry.items() if k not in ("public_id", "created_at")},
            {
                "name": "Imidacloprid",
                "description": "Store spray",
                "company_name": "Bayer",
                "price": "1850.50",
                "quantity": "5.000",
                "unit": "litre",
                "created_by": {"id": self.stock_admin.id, "name": "stock admin"},
            },
        )

        listing = self.client.get(ENTRIES_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["total_count"], 1)
        (row,) = listing.data["results"]
        row.pop("created_at")
        entry.pop("created_at")
        self.assertEqual(row, entry)
        self.assertIn("available_filters", listing.data)
        self.assertIn("available_sorts", listing.data)

    def test_optional_fields_may_be_left_out(self):
        """tests/test_non_stock_inward_api.py::NonStockInwardApiTest::test_optional_fields_may_be_left_out"""
        self.login_as(self.stock_admin)
        response = self.client.post(
            ENTRIES_URL, {"name": "Sieve", "quantity": "2", "unit": "count"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data["description"], "")
        self.assertEqual(response.data["company_name"], "")
        self.assertIsNone(response.data["price"])

        nulls = self._create(name="Gloves", description=None, company_name=None, price=None)
        self.assertEqual(nulls.status_code, status.HTTP_201_CREATED, nulls.content)
        self.assertEqual(
            (nulls.data["description"], nulls.data["company_name"], nulls.data["price"]),
            ("", "", None),
        )

    def test_invalid_create_bodies_are_400(self):
        """tests/test_non_stock_inward_api.py::NonStockInwardApiTest::test_invalid_create_bodies_are_400"""
        self.login_as(self.stock_admin)
        for label, overrides in (
            ("blank name", {"name": "  "}),
            ("zero quantity", {"quantity": "0"}),
            ("negative quantity", {"quantity": "-1"}),
            ("unknown unit", {"unit": "bucket"}),
            ("negative price", {"price": "-0.01"}),
            ("missing unit", {"unit": None}),
        ):
            with self.subTest(case=label):
                response = self._create(**overrides)
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.content
                )
        self.assertFalse(NonStockInward.objects.exists())

    # -- filters --------------------------------------------------------------

    def test_filters_and_sorts(self):
        """tests/test_non_stock_inward_api.py::NonStockInwardApiTest::test_filters_and_sorts"""
        self.login_as(self.stock_admin)
        self._create(name="Bolt", company_name="Rajkot Works", unit="count")
        self._create(name="Acephate", company_name="UPL", unit="kg")

        def names(**params):
            response = self.client.get(ENTRIES_URL, params)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
            return [row["name"] for row in response.data["results"]]

        self.assertEqual(names(), ["Acephate", "Bolt"])  # newest first
        self.assertEqual(names(sort="name"), ["Acephate", "Bolt"])
        self.assertEqual(names(unit="count"), ["Bolt"])
        self.assertEqual(names(name="cep"), ["Acephate"])
        self.assertEqual(names(company_name="rajkot"), ["Bolt"])

    # -- patch + delete -------------------------------------------------------

    def test_patch_changes_only_what_is_sent_and_delete_soft_deletes(self):
        """tests/test_non_stock_inward_api.py::NonStockInwardApiTest::test_patch_changes_only_what_is_sent_and_delete_soft_deletes"""
        self.login_as(self.stock_admin)
        public_id = self._create().data["public_id"]

        response = self.client.patch(
            self._url(public_id), {"quantity": "7.5", "price": None}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["quantity"], "7.500")
        self.assertIsNone(response.data["price"])
        self.assertEqual(response.data["name"], "Imidacloprid")
        entry = NonStockInward.objects.get(public_id=public_id)
        self.assertEqual(entry.quantity, Decimal("7.500"))
        self.assertIsNone(entry.price)
        self.assertEqual(entry.unit, "litre")

        for label, body in (
            ("empty", {}),
            ("blank name", {"name": ""}),
            ("zero quantity", {"quantity": "0"}),
            ("unknown unit", {"unit": "bucket"}),
        ):
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.patch(self._url(public_id), body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        self.assertEqual(
            self.client.delete(self._url(public_id)).status_code, status.HTTP_204_NO_CONTENT
        )
        entry = NonStockInward.all_objects.get(public_id=public_id)
        self.assertTrue(entry.is_deleted)
        self.assertEqual(entry.deleted_by_id, self.stock_admin.id)
        self.assertEqual(self.client.get(ENTRIES_URL).data["total_count"], 0)
        for verb in ("patch", "delete"):
            with self.subTest(gone=verb):
                response = getattr(self.client, verb)(
                    self._url(public_id), {"name": "X"}, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- permissions ----------------------------------------------------------

    def test_any_admin_may_list_but_only_stock_admins_may_write(self):
        """tests/test_non_stock_inward_api.py::NonStockInwardApiTest::test_any_admin_may_list_but_only_stock_admins_may_write"""
        self.login_as(self.stock_admin)
        public_id = self._create().data["public_id"]

        self.login_as(self.plain_admin)
        self.assertEqual(self.client.get(ENTRIES_URL).status_code, status.HTTP_200_OK)
        refused = {
            "create": self._create(name="Other"),
            "update": self.client.patch(self._url(public_id), {"name": "X"}, format="json"),
            "delete": self.client.delete(self._url(public_id)),
        }
        for action, response in refused.items():
            with self.subTest(admin="plain", action=action):
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(NonStockInward.objects.get().name, "Imidacloprid")

        self.login_as(self.nobody)
        self.assertEqual(self.client.get(ENTRIES_URL).status_code, status.HTTP_403_FORBIDDEN)

        self.clear_auth()
        self.assertIn(
            self.client.get(ENTRIES_URL).status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
