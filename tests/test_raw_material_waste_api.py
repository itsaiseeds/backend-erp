"""ORM-backed tests for the raw-material waste endpoints (list/create + delete).

Uses the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and adds its own app admin in ``setUpTestData``. The product (SAI-33, whose bag
is 1kg x 40 = 40kg) comes from ``dml.sql``; the party is created in this fixture.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations
from aggregator.models import (
    InwardRawMaterial,
    Party,
    Product,
    ProductPackaging,
    RawMaterialWaste,
    StatusIds,
)
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

WASTES_URL = "/api/sales-admin/raw-material-wastes"
WASTE_URL = "/api/sales-admin/raw-material-waste"
STOCK_URL = "/api/sales-admin/raw-material-stock"


class RawMaterialWasteApiTest(WebApiTestCase):
    """Waste rows deduct from the unpacked raw pool and are reversible.

    tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin, a seeded product and a party."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
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
        cls.product = Product.objects.get(name="SAI-33")
        cls.party = Party.objects.create(
            name="ABC Traders", city_id=1, created_by=cls.seed_admin
        )

    # -- helpers --------------------------------------------------------------

    def _stock_in(self, kg: str = "100", status_id: int = StatusIds.IN_USE.value) -> None:
        """Book an already-effective raw lot of ``kg`` for the product (default In Use)."""
        InwardRawMaterial.objects.create(
            product=self.product,
            party=self.party,
            lot_no="SUP-T1",
            quantity_kg=Decimal(kg),
            status_id=status_id,
            effective_date=InventoryOperations.today(),
            created_by=self.seed_admin,
        )

    def _waste(self, **overrides):
        """POST a waste row (defaults: SAI-33 / 10 kg / 'rain damage')."""
        body = {
            "product": self.product.public_id,
            "quantity_kg": "10",
            "reason": "rain damage",
            **overrides,
        }
        return self.client.post(WASTES_URL, body, format="json")

    def _stock_line(self) -> dict:
        response = self.client.get(STOCK_URL, {"product": self.product.public_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        return response.data["lines"][0]

    # -- creation -------------------------------------------------------------

    def test_recording_waste_returns_the_row_and_stores_it(self):
        """POST writes a WS- row with product, kg and reason, and no date input.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_recording_waste_returns_the_row_and_stores_it
        """
        self.login_as(self.seed_admin)
        self._stock_in()
        response = self._waste()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)

        self.assertTrue(response.data["public_id"].startswith("WS-"))
        self.assertEqual(
            response.data["product"], {"public_id": self.product.public_id, "name": "SAI-33"}
        )
        self.assertEqual(response.data["quantity_kg"], "10.000")
        self.assertEqual(response.data["reason"], "rain damage")

        stored = RawMaterialWaste.objects.get(public_id=response.data["public_id"])
        self.assertEqual(stored.created_by_id, self.seed_admin.id)

    def test_reason_is_optional(self):
        """A waste row may omit its reason.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_reason_is_optional
        """
        self.login_as(self.seed_admin)
        self._stock_in()
        response = self.client.post(
            WASTES_URL,
            {"product": self.product.public_id, "quantity_kg": "5"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data["reason"], "")

    def test_missing_or_invalid_fields_are_400(self):
        """Missing product / quantity, non-positive kg and unknown product are rejected.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_missing_or_invalid_fields_are_400
        """
        self.login_as(self.seed_admin)
        self._stock_in()
        cases = [
            ("missing product", {"quantity_kg": "10"}),
            ("missing quantity", {"product": self.product.public_id}),
            ("zero", {"product": self.product.public_id, "quantity_kg": "0"}),
            ("negative", {"product": self.product.public_id, "quantity_kg": "-1"}),
            ("unknown product", {"product": "P-NOPE", "quantity_kg": "10"}),
        ]
        for label, body in cases:
            with self.subTest(label):
                response = self.client.post(WASTES_URL, body, format="json")
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.content
                )
        self.assertFalse(RawMaterialWaste.objects.exists())

    # -- stock effect ---------------------------------------------------------

    def test_waste_lowers_available_raw_and_shows_on_the_stock_report(self):
        """wasted_kg is reported and subtracted from available_kg.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_waste_lowers_available_raw_and_shows_on_the_stock_report
        """
        self.login_as(self.seed_admin)
        self._stock_in("100")
        self._waste(quantity_kg="10")
        self._waste(quantity_kg="5.5")

        line = self._stock_line()
        self.assertEqual(line["incoming_kg"], "100.000")
        self.assertEqual(line["packed_kg"], "0.000")
        self.assertEqual(line["wasted_kg"], "15.500")
        self.assertEqual(line["available_kg"], "84.500")

    def test_waste_beyond_unpacked_raw_is_refused_and_not_written(self):
        """More waste than unpacked raw is a 400 and leaves no row behind.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_waste_beyond_unpacked_raw_is_refused_and_not_written
        """
        self.login_as(self.seed_admin)
        self._stock_in("100")
        pack = ProductPackaging.objects.get(product=self.product)
        InventoryOperations.record_stock_count(
            product_packaging=pack, bags=2, actor=self.seed_admin  # 80kg packed -> 20 left
        )

        response = self._waste(quantity_kg="20.001")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertFalse(RawMaterialWaste.objects.exists())

        self.assertEqual(self._waste(quantity_kg="20").status_code, status.HTTP_201_CREATED)

    def test_rejected_kilograms_cannot_back_a_waste_entry(self):
        """A reached Rejected lot is reported as rejected_kg but is never wasteable.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_rejected_kilograms_cannot_back_a_waste_entry
        """
        self.login_as(self.seed_admin)
        self._stock_in("50")
        self._stock_in("80", status_id=StatusIds.RAW_MATERIAL_REJECTED.value)

        over_in_use = self._waste(quantity_kg="60")  # only the 50 kg In Use counts
        self.assertEqual(over_in_use.status_code, status.HTTP_400_BAD_REQUEST, over_in_use.content)
        self.assertEqual(self._waste(quantity_kg="50").status_code, status.HTTP_201_CREATED)

        line = self._stock_line()
        self.assertEqual(line["rejected_kg"], "80.000")
        self.assertEqual(line["wasted_kg"], "50.000")
        self.assertEqual(line["available_kg"], "0.000")

    def test_wasted_kilograms_cannot_be_packed(self):
        """A count that needs kilograms already written off is refused.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_wasted_kilograms_cannot_be_packed
        """
        self.login_as(self.seed_admin)
        self._stock_in("100")
        self._waste(quantity_kg="30")  # 70 left: two bags (80kg) no longer fit
        pack = ProductPackaging.objects.get(product=self.product)

        with self.assertRaises(ValueError):
            InventoryOperations.record_stock_count(
                product_packaging=pack, bags=2, actor=self.seed_admin
            )
        InventoryOperations.record_stock_count(
            product_packaging=pack, bags=1, actor=self.seed_admin
        )

    def test_an_inward_lot_covering_waste_cannot_be_deleted(self):
        """Removing the lot that backs waste would leave raw negative, so it is refused.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_an_inward_lot_covering_waste_cannot_be_deleted
        """
        self.login_as(self.seed_admin)
        self._stock_in("100")
        self._waste(quantity_kg="10")
        lot = InwardRawMaterial.objects.get(product=self.product)

        response = self.client.delete(f"/api/sales-admin/inward-raw-material/{lot.public_id}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    # -- deletion -------------------------------------------------------------

    def test_deleting_waste_gives_the_kilograms_back(self):
        """DELETE soft-deletes the row, restores available_kg, and the row is gone (404).

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_deleting_waste_gives_the_kilograms_back
        """
        self.login_as(self.seed_admin)
        self._stock_in("100")
        created = self._waste(quantity_kg="10")
        self.assertEqual(self._stock_line()["available_kg"], "90.000")

        url = f"{WASTE_URL}/{created.data['public_id']}"
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(self._stock_line()["available_kg"], "100.000")
        self.assertTrue(
            RawMaterialWaste.all_objects.get(public_id=created.data["public_id"]).is_deleted
        )
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        listed = self.client.get(WASTES_URL).data["results"]
        self.assertNotIn(created.data["public_id"], {row["public_id"] for row in listed})

    # -- listing --------------------------------------------------------------

    def test_list_is_newest_first_and_filters_and_sorts_by_product_and_quantity(self):
        """Default order is newest first; ?product= filters; sort=quantity_kg orders by kg.

        tests/test_raw_material_waste_api.py::RawMaterialWasteApiTest::test_list_is_newest_first_and_filters_and_sorts_by_product_and_quantity
        """
        self.login_as(self.seed_admin)
        self._stock_in("100")
        first = self._waste(quantity_kg="30").data["public_id"]
        second = self._waste(quantity_kg="5").data["public_id"]

        listed = self.client.get(WASTES_URL)
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.content)
        self.assertEqual([row["public_id"] for row in listed.data["results"]], [second, first])

        by_kg = self.client.get(WASTES_URL, {"sort": "quantity_kg"})
        self.assertEqual([row["public_id"] for row in by_kg.data["results"]], [second, first])

        none = self.client.get(WASTES_URL, {"product": "P-DOES-NOT-EXIST"})
        self.assertEqual(none.data["results"], [])
        mine = self.client.get(WASTES_URL, {"product": self.product.public_id})
        self.assertEqual(len(mine.data["results"]), 2)
