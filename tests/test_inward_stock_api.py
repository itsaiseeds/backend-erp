"""ORM-backed tests for the read-time stock aggregate endpoints.

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own app admin in ``setUpTestData``. Lots are planted directly via
the ORM to declare exact status / effective_date states, then the two aggregate
endpoints are checked against them.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InwardOperations
from aggregator.models import (
    InwardOtherMaterial,
    InwardRawMaterial,
    InwardRawMaterialStatus,
    OtherMaterialRecipe,
    OtherMaterialType,
    Party,
    Product,
)
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

RAW_STOCK_URL = "/api/sales-admin/raw-material-stock"
OTHER_STOCK_URL = "/api/sales-admin/other-material-stock"


class InwardStockApiTest(WebApiTestCase):
    """Cover the gate both reads apply: dated, reached, alive, and (raw) in use.

    tests/test_inward_stock_api.py::InwardStockApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin and the master-data / recipes used by the lots."""
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

        cls.today = InwardOperations.today()
        cls.tomorrow = cls.today + timedelta(days=1)

        cls.product1 = Product.objects.get(name="SAI-33")
        cls.product2 = Product.objects.get(name="SAI-3353")
        cls.party = Party.objects.create(
            name="ABC Traders", city_id=1, created_by=cls.seed_admin
        )
        cls.leaflets = OtherMaterialType.objects.get(name="leaflets")
        cls.bag_cover = OtherMaterialType.objects.get(name="bag_outer_cover")

        cls.leaflet_recipe = OtherMaterialRecipe.objects.create(
            product=cls.product1,
            material_type=cls.leaflets,
            packet_weight=Decimal("1.000"),
            quantity=Decimal("2.000"),
            created_by=cls.seed_admin,
        )
        cls.bag_recipe = OtherMaterialRecipe.objects.create(
            product=cls.product2,
            material_type=cls.bag_cover,
            packet_weight=Decimal("1.000"),
            quantity=Decimal("1.000"),
            created_by=cls.seed_admin,
        )

    # -- fixtures -------------------------------------------------------------

    def _set_up_raw_lots(self):
        """Plant a containing lot plus three states that must NOT count."""
        self._counting_raw = InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            quantity_kg=Decimal("100"),
            effective_date=self.today,
            status=InwardRawMaterialStatus.IN_USE,
            created_by=self.seed_admin,
        )
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            quantity_kg=Decimal("20"),
            effective_date=self.today,
            status=InwardRawMaterialStatus.LAB_TESTING,  # not cleared by the lab
            created_by=self.seed_admin,
        )
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            quantity_kg=Decimal("50"),
            effective_date=self.tomorrow,  # dated, but not reached yet
            status=InwardRawMaterialStatus.IN_USE,
            created_by=self.seed_admin,
        )
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            quantity_kg=Decimal("30"),
            effective_date=None,  # never dated
            status=InwardRawMaterialStatus.IN_USE,
            created_by=self.seed_admin,
        )
        deleted_dated = InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            quantity_kg=Decimal("10"),
            effective_date=self.today,
            status=InwardRawMaterialStatus.IN_USE,
            created_by=self.seed_admin,
        )
        deleted_dated.mark_deleted(self.seed_admin)

    def _set_up_other_lots(self):
        """Plant a counting entry plus three states that must NOT count."""
        self._counting_other = InwardOtherMaterial.objects.create(
            recipe=self.leaflet_recipe,
            party=self.party,
            quantity=Decimal("6"),
            effective_date=self.today,
            created_by=self.seed_admin,
        )
        InwardOtherMaterial.objects.create(
            recipe=self.leaflet_recipe,
            party=self.party,
            quantity=Decimal("10"),
            effective_date=self.tomorrow,  # dated, but not reached yet
            created_by=self.seed_admin,
        )
        InwardOtherMaterial.objects.create(
            recipe=self.leaflet_recipe,
            party=self.party,
            quantity=Decimal("4"),
            effective_date=None,  # never dated
            created_by=self.seed_admin,
        )
        deleted_dated = InwardOtherMaterial.objects.create(
            recipe=self.leaflet_recipe,
            party=self.party,
            quantity=Decimal("8"),
            effective_date=self.today,
            created_by=self.seed_admin,
        )
        deleted_dated.mark_deleted(self.seed_admin)

    # -- raw-material stock ---------------------------------------------------

    def test_raw_stock_counts_only_dated_in_use_live_lots(self):
        """Lab_state, future dates, undated and deleted lots all fall out.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_raw_stock_counts_only_dated_in_use_live_lots
        """
        self.login_as(self.seed_admin)
        self._set_up_raw_lots()

        response = self.client.get(RAW_STOCK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["as_of"], self.today.isoformat())
        self.assertEqual(len(response.data["lines"]), 1)
        self.assertEqual(response.data["lines"][0], {
            "product": self.product1.public_id,
            "name": "SAI-33",
            "incoming_kg": "100.000",
            "packed_kg": "0.000",
            "available_kg": "100.000",
        })

    def test_raw_stock_sums_multiple_lots_and_supports_product_filtering(self):
        """Two counting lots add up; ?product narrows the report to one line.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_raw_stock_sums_multiple_lots_and_supports_product_filtering
        """
        self.login_as(self.seed_admin)
        self._set_up_raw_lots()
        InwardRawMaterial.objects.create(
            product=self.product2,
            party=self.party,
            quantity_kg=Decimal("7"),
            effective_date=self.today,
            status=InwardRawMaterialStatus.IN_USE,
            created_by=self.seed_admin,
        )

        response = self.client.get(RAW_STOCK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        lines = {line["product"]: line for line in response.data["lines"]}
        self.assertEqual(lines[self.product1.public_id]["incoming_kg"], "100.000")
        self.assertEqual(lines[self.product2.public_id]["incoming_kg"], "7.000")

        filtered = self.client.get(
            f"{RAW_STOCK_URL}?product={self.product1.public_id}"
        )
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(len(filtered.data["lines"]), 1)
        self.assertEqual(filtered.data["lines"][0]["product"], self.product1.public_id)

    def test_a_flipped_lot_counts_against_the_stock_read(self):
        """The API lifecycle (book -> flip, which dates the lot) feeds raw-material stock.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_a_flipped_lot_counts_against_the_stock_read
        """
        self.login_as(self.seed_admin)
        created = self.client.post(
            "/api/sales-admin/inward-raw-materials",
            {
                "product": self.product1.id,
                "party": self.party.id,
                "quantity_kg": "25",
                "lab_sampling_date": self.today.isoformat(),
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = f"/api/sales-admin/inward-raw-material/{created.data['public_id']}"
        flipped = self.client.patch(
            url,
            {"status": "in_use"},
            format="json",
        )
        self.assertEqual(flipped.status_code, status.HTTP_200_OK, flipped.content)
        self.assertEqual(flipped.data["effective_date"], self.today.isoformat())

        response = self.client.get(
            f"{RAW_STOCK_URL}?product={self.product1.public_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["lines"], [{
            "product": self.product1.public_id,
            "name": "SAI-33",
            "incoming_kg": "25.000",
            "packed_kg": "0.000",
            "available_kg": "25.000",
        }])

    def test_a_reverted_lot_stops_counting_against_the_stock_read(self):
        """Reverting to lab_testing clears the stamp and drops the lot from stock.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_a_reverted_lot_stops_counting_against_the_stock_read
        """
        self.login_as(self.seed_admin)
        created = self.client.post(
            "/api/sales-admin/inward-raw-materials",
            {
                "product": self.product1.id,
                "party": self.party.id,
                "quantity_kg": "25",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = f"/api/sales-admin/inward-raw-material/{created.data['public_id']}"

        flipped = self.client.patch(url, {"status": "in_use"}, format="json")
        self.assertEqual(flipped.status_code, status.HTTP_200_OK, flipped.content)

        counting = self.client.get(f"{RAW_STOCK_URL}?product={self.product1.public_id}")
        self.assertEqual(counting.status_code, status.HTTP_200_OK)
        self.assertEqual(counting.data["lines"], [{
            "product": self.product1.public_id,
            "name": "SAI-33",
            "incoming_kg": "25.000",
            "packed_kg": "0.000",
            "available_kg": "25.000",
        }])

        reverted = self.client.patch(url, {"status": "lab_testing"}, format="json")
        self.assertEqual(reverted.status_code, status.HTTP_200_OK, reverted.content)
        self.assertIsNone(reverted.data["effective_date"])

        empty = self.client.get(f"{RAW_STOCK_URL}?product={self.product1.public_id}")
        self.assertEqual(empty.status_code, status.HTTP_200_OK)
        self.assertEqual(empty.data["lines"], [])

    # -- other-material stock -------------------------------------------------

    def test_other_stock_counts_only_dated_live_lots_per_material_type(self):
        """Future dates, undated and deleted entries fall out; unit comes along.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_other_stock_counts_only_dated_live_lots_per_material_type
        """
        self.login_as(self.seed_admin)
        self._set_up_other_lots()
        InwardOtherMaterial.objects.create(
            recipe=self.bag_recipe,
            party=self.party,
            quantity=Decimal("2"),
            effective_date=self.today,
            created_by=self.seed_admin,
        )

        response = self.client.get(OTHER_STOCK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["as_of"], self.today.isoformat())
        lines = {line["material_type"]["id"]: line for line in response.data["lines"]}
        self.assertEqual(lines[self.leaflets.id], {
            "material_type": {"id": 3, "name": "leaflets", "unit_type": "count"},
            "on_hand": "6.000",
        })
        self.assertEqual(lines[self.bag_cover.id], {
            "material_type": {"id": 1, "name": "bag_outer_cover", "unit_type": "kg"},
            "on_hand": "2.000",
        })

    def test_other_stock_supports_material_type_filtering(self):
        """?material_type narrows the report to the requested type only.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_other_stock_supports_material_type_filtering
        """
        self.login_as(self.seed_admin)
        self._set_up_other_lots()
        InwardOtherMaterial.objects.create(
            recipe=self.bag_recipe,
            party=self.party,
            quantity=Decimal("2"),
            effective_date=self.today,
            created_by=self.seed_admin,
        )

        response = self.client.get(f"{OTHER_STOCK_URL}?material_type={self.leaflets.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data["lines"]), 1)
        self.assertEqual(response.data["lines"][0]["on_hand"], "6.000")
        self.assertEqual(response.data["lines"][0]["material_type"]["id"], self.leaflets.id)

        self.assertEqual(
            self.client.get(f"{OTHER_STOCK_URL}?material_type=not-an-int").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
