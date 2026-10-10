"""Godown manager raw-material waste: ``godown/raw-material-wastes`` and ``godown/raw-material-waste/<id>``.

A godown manager may add, list, edit and delete waste entries -- and nothing
else of the waste side (waste orders are admin-only). Role gating itself is
owned by ``tests/test_view_contracts.py``; this proves the endpoints work, that
the rules the admin side has also hold here, and that the godown token reaches
no waste-order endpoint.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations
from aggregator.models import (
    InwardRawMaterial,
    Party,
    PartyType,
    Product,
    RawMaterialWaste,
    StatusIds,
)
from authentication.models import Admin
from tests.android.common import AndroidApiTestCase

User = get_user_model()

LIST_URL = "/android/api/v1/godown/raw-material-wastes"
ITEM_URL = "/android/api/v1/godown/raw-material-waste/{public_id}"
STOCK_URL = "/android/api/v1/godown/raw-material-stock"


class GodownRawMaterialWasteApiTest(AndroidApiTestCase):
    """tests/test_godown_raw_material_waste_api.py::GodownRawMaterialWasteApiTest"""

    # Raw lots are seeded through the ORM on purpose (see test_raw_material_waste_api).
    stock_ledger_guard = False

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        cls.godown = User.objects.get(phone_number="3333333333")
        cls.lab_tester = User.objects.get(phone_number="4545454545")
        cls.sales_person = User.objects.get(phone_number="0000000000")
        cls.seed_admin = User.objects.create_user(
            phone_number="7777777777",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.seed_admin, created_by=cls.superuser)
        cls.product = Product.objects.get(name="SAI-33")
        cls.party = Party.objects.create(
            name="ABC Traders", city_id=1, party_type=PartyType.RAW_MATERIAL, created_by=cls.seed_admin
        )

    def setUp(self):
        super().setUp()
        InwardRawMaterial.objects.create(
            product=self.product,
            party=self.party,
            lot_no="SUP-T1",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("100"),
            status_id=StatusIds.IN_USE.value,
            effective_date=InventoryOperations.today(),
            created_by=self.seed_admin,
        )
        self.login_as(self.godown)

    def _add(self, **overrides):
        body = {
            "product": self.product.public_id,
            "quantity_kg": "10",
            "reason": "rain damage",
            **overrides,
        }
        return self.client.post(LIST_URL, body, format="json")

    def test_a_godown_manager_can_add_list_edit_and_delete_waste(self):
        """tests/test_godown_raw_material_waste_api.py::GodownRawMaterialWasteApiTest::test_a_godown_manager_can_add_list_edit_and_delete_waste"""
        created = self._add()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        self.assertTrue(created.data["public_id"].startswith("WS-"))
        self.assertEqual(created.data["quantity_kg"], "10.000")
        self.assertEqual(created.data["reason"], "rain damage")
        row = RawMaterialWaste.objects.get(public_id=created.data["public_id"])
        self.assertEqual(row.created_by, self.godown)
        self.assertEqual(InventoryOperations.raw_wasted_kg(self.product), Decimal("10"))

        listed = self.client.get(LIST_URL, {"product": self.product.public_id})
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.content)
        self.assertEqual([r["public_id"] for r in listed.data["results"]], [row.public_id])

        url = ITEM_URL.format(public_id=row.public_id)
        patched = self.client.patch(url, {"quantity_kg": "25", "reason": "flood"}, format="json")
        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.content)
        self.assertEqual(patched.data["quantity_kg"], "25.000")
        self.assertEqual(patched.data["reason"], "flood")
        self.assertEqual(InventoryOperations.raw_wasted_kg(self.product), Decimal("25"))
        # It shows on the godown manager's own stock view, read-only as before.
        stock = self.client.get(STOCK_URL, {"product": self.product.public_id})
        self.assertEqual(stock.data["lines"][0]["wasted_kg"], "25.000")

        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(InventoryOperations.raw_wasted_kg(self.product), Decimal("0"))
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(LIST_URL).data["results"], [])

    def test_the_same_rules_as_the_admin_side_hold(self):
        """More than the unpacked raw is refused on add and on edit; bad input is a 400.

        tests/test_godown_raw_material_waste_api.py::GodownRawMaterialWasteApiTest::test_the_same_rules_as_the_admin_side_hold
        """
        self.assertEqual(self._add(quantity_kg="100.001").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._add(quantity_kg="0").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._add(product="P-NOPE").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(RawMaterialWaste.objects.exists())

        row = RawMaterialWaste.objects.get(public_id=self._add(quantity_kg="60").data["public_id"])
        over = self.client.patch(
            ITEM_URL.format(public_id=row.public_id), {"quantity_kg": "100.5"}, format="json"
        )
        self.assertEqual(over.status_code, status.HTTP_400_BAD_REQUEST)
        row.refresh_from_db()
        self.assertEqual(row.quantity_kg, Decimal("60"))

    def test_only_a_godown_manager_can_use_it(self):
        """A lab tester, a salesperson and an anonymous caller are refused on every verb.

        tests/test_godown_raw_material_waste_api.py::GodownRawMaterialWasteApiTest::test_only_a_godown_manager_can_use_it
        """
        row = RawMaterialWaste.objects.get(public_id=self._add().data["public_id"])
        url = ITEM_URL.format(public_id=row.public_id)

        for who, user in (("lab tester", self.lab_tester), ("salesperson", self.sales_person), ("anonymous", None)):
            with self.subTest(who=who):
                self.clear_auth()
                if user is not None:
                    self.login_as(user)
                refused = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
                self.assertIn(self.client.get(LIST_URL).status_code, refused)
                self.assertIn(self._add().status_code, refused)
                self.assertIn(self.client.patch(url, {"quantity_kg": "1"}, format="json").status_code, refused)
                self.assertIn(self.client.delete(url).status_code, refused)

        row.refresh_from_db()
        self.assertFalse(row.is_deleted)
        self.assertEqual(row.quantity_kg, Decimal("10"))
        self.assertEqual(RawMaterialWaste.objects.count(), 1)

    def test_a_godown_token_reaches_no_waste_order_endpoint(self):
        """Waste orders (and the admin waste routes) stay admin-only.

        tests/test_godown_raw_material_waste_api.py::GodownRawMaterialWasteApiTest::test_a_godown_token_reaches_no_waste_order_endpoint
        """
        refused = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        for method, path in (
            ("get", "/api/sales-admin/waste-orders/"),
            ("post", "/api/sales-admin/create-waste-order"),
            ("patch", "/api/sales-admin/edit-waste-order/CORD-X"),
            ("post", "/api/sales-admin/dispatch-waste-order/CORD-X"),
            ("get", "/api/sales-admin/raw-material-wastes"),
            ("post", "/api/sales-admin/raw-material-wastes"),
        ):
            with self.subTest(path=path):
                response = getattr(self.client, method)(path, {}, format="json") if method != "get" else self.client.get(path)
                self.assertIn(response.status_code, refused)
        # And there is no Android waste-order route to find.
        self.assertEqual(
            self.client.get("/android/api/v1/godown/waste-orders/").status_code, status.HTTP_404_NOT_FOUND
        )
