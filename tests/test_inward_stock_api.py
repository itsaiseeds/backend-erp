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

from aggregator import InventoryOperations, InwardOperations
from aggregator.models import (
    InwardOtherMaterial,
    InwardRawMaterial,
    OtherMaterialRecipe,
    OtherMaterialType,
    Party,
    PartyType,
    Product,
    ProductPackaging,
    StatusIds,
)
from authentication.models import Admin
from tests.common import WebApiTestCase, lab_verdict

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

RAW_STOCK_URL = "/api/sales-admin/raw-material-stock"
OTHER_STOCK_URL = "/api/sales-admin/other-material-stock"


class InwardStockApiTest(WebApiTestCase):
    """Cover the gate both reads apply: dated, reached, alive, and (raw) in use.

    tests/test_inward_stock_api.py::InwardStockApiTest
    """

    # Seeds stock through raw ORM on purpose (dispatches, lots and status flips written
    # directly), so the stock ledger is not expected to follow -- see
    # DMLTestCase.stock_ledger_guard.
    stock_ledger_guard = False


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
            name="ABC Traders", city_id=1, party_type=PartyType.RAW_MATERIAL, created_by=cls.seed_admin
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
            lot_no="LOT-COUNTING",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("100"),
            effective_date=self.today,
            status_id=StatusIds.IN_USE.value,
            created_by=self.seed_admin,
        )
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            lot_no="LOT-LAB-TESTING",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("20"),
            effective_date=self.today,
            status_id=StatusIds.LAB_TESTING.value,  # not cleared by the lab
            created_by=self.seed_admin,
        )
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            lot_no="LOT-FUTURE",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("50"),
            effective_date=self.tomorrow,  # dated, but not reached yet
            status_id=StatusIds.IN_USE.value,
            created_by=self.seed_admin,
        )
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            lot_no="LOT-UNDATED",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("30"),
            effective_date=None,  # never dated
            status_id=StatusIds.IN_USE.value,
            created_by=self.seed_admin,
        )
        deleted_dated = InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            lot_no="LOT-DELETED",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("10"),
            effective_date=self.today,
            status_id=StatusIds.IN_USE.value,
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
            "is_usable": True,
            "incoming_kg": "100.000",
            "packed_kg": "0.000",
            "wasted_kg": "0.000",
            "available_kg": "100.000",
            "rejected_kg": "0.000",
            "waste_reserved_kg": "0.000",
            "waste_consumed_kg": "0.000",
            "waste_available_kg": "0.000",
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
            lot_no="LOT-P2",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("7"),
            effective_date=self.today,
            status_id=StatusIds.IN_USE.value,
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
                "product": self.product1.public_id,
                "party": self.party.id,
                "lot_no": "LOT-FLIP",
                "farmer_name": "Test Farmer",
                "quantity_kg": "25",
                "lab_sampling_date": self.today.isoformat(),
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        passed = lab_verdict(created.data["public_id"], "Pass", actor=self.seed_admin)
        self.assertEqual(passed.inward_raw_material.effective_date, self.today)

        response = self.client.get(
            f"{RAW_STOCK_URL}?product={self.product1.public_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["lines"], [{
            "product": self.product1.public_id,
            "name": "SAI-33",
            "is_usable": True,
            "incoming_kg": "25.000",
            "packed_kg": "0.000",
            "wasted_kg": "0.000",
            "available_kg": "25.000",
            "rejected_kg": "0.000",
            "waste_reserved_kg": "0.000",
            "waste_consumed_kg": "0.000",
            "waste_available_kg": "0.000",
        }])

    def test_a_reverted_lot_stops_counting_against_the_stock_read(self):
        """Reverting to lab_testing clears the stamp and drops the lot from stock.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_a_reverted_lot_stops_counting_against_the_stock_read
        """
        self.login_as(self.seed_admin)
        created = self.client.post(
            "/api/sales-admin/inward-raw-materials",
            {
                "product": self.product1.public_id,
                "party": self.party.id,
                "lot_no": "LOT-REVERT",
                "farmer_name": "Test Farmer",
                "quantity_kg": "25",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = f"/api/sales-admin/inward-raw-material/{created.data['public_id']}"

        lab_verdict(created.data["public_id"], "Pass", actor=self.seed_admin)

        counting = self.client.get(f"{RAW_STOCK_URL}?product={self.product1.public_id}")
        self.assertEqual(counting.status_code, status.HTTP_200_OK)
        self.assertEqual(counting.data["lines"], [{
            "product": self.product1.public_id,
            "name": "SAI-33",
            "is_usable": True,
            "incoming_kg": "25.000",
            "packed_kg": "0.000",
            "wasted_kg": "0.000",
            "available_kg": "25.000",
            "rejected_kg": "0.000",
            "waste_reserved_kg": "0.000",
            "waste_consumed_kg": "0.000",
            "waste_available_kg": "0.000",
        }])

        reverted = self.client.patch(url, {"status": "Lab Testing"}, format="json")
        self.assertEqual(reverted.status_code, status.HTTP_200_OK, reverted.content)
        self.assertIsNone(reverted.data["effective_date"])

        empty = self.client.get(f"{RAW_STOCK_URL}?product={self.product1.public_id}")
        self.assertEqual(empty.status_code, status.HTTP_200_OK)
        self.assertEqual(empty.data["lines"], [])

    # -- rejected stock ---------------------------------------------------

    def test_rejected_kg_is_reported_but_never_packable(self):
        """PRD acceptance scenario: three lots, one In Use, one Rejected, one
        still Lab Testing -- rejected_kg is its own bucket, never folded into
        incoming/available, and a bag count cannot spend it.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_rejected_kg_is_reported_but_never_packable
        """
        self.login_as(self.seed_admin)
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            lot_no="SUP-2026-A1",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("1000"),
            effective_date=self.today,
            status_id=StatusIds.IN_USE.value,
            created_by=self.seed_admin,
        )
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            lot_no="SUP-2026-B7",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("500"),
            effective_date=self.today,
            status_id=StatusIds.RAW_MATERIAL_REJECTED.value,
            created_by=self.seed_admin,
        )
        InwardRawMaterial.objects.create(
            product=self.product1,
            party=self.party,
            lot_no="SUP-2026-C3",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("250"),
            status_id=StatusIds.LAB_TESTING.value,  # stays Lab Testing, undated
            created_by=self.seed_admin,
        )

        response = self.client.get(f"{RAW_STOCK_URL}?product={self.product1.public_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["lines"], [{
            "product": self.product1.public_id,
            "name": "SAI-33",
            "is_usable": True,
            "incoming_kg": "1000.000",
            "packed_kg": "0.000",
            "wasted_kg": "0.000",
            "available_kg": "1000.000",
            "rejected_kg": "500.000",
            "waste_reserved_kg": "0.000",
            "waste_consumed_kg": "0.000",
            "waste_available_kg": "0.000",
        }])

        # A bag count needing more than the 1000 kg In Use is refused -- the
        # rejected 500 kg cannot be packed. SAI-33's packaging is 1kg x 40
        # packets = 40kg/bag, so 26 bags (1040kg) is just over the limit.
        pack = ProductPackaging.objects.get(product=self.product1)
        with self.assertRaises(ValueError):
            InventoryOperations.record_stock_count(
                product_packaging=pack, bags=26, actor=self.seed_admin
            )

    def test_a_product_whose_entire_intake_is_rejected_still_appears(self):
        """A product with no In Use lot at all is still listed, with 0/0/0
        plus its rejected kilograms -- rejected stock is never silently
        invisible.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_a_product_whose_entire_intake_is_rejected_still_appears
        """
        self.login_as(self.seed_admin)
        InwardRawMaterial.objects.create(
            product=self.product2,
            party=self.party,
            lot_no="SUP-REJ-ONLY",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("80"),
            effective_date=self.today,
            status_id=StatusIds.RAW_MATERIAL_REJECTED.value,
            created_by=self.seed_admin,
        )

        response = self.client.get(f"{RAW_STOCK_URL}?product={self.product2.public_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["lines"], [{
            "product": self.product2.public_id,
            "name": "SAI-3353",
            "is_usable": True,
            "incoming_kg": "0.000",
            "packed_kg": "0.000",
            "wasted_kg": "0.000",
            "available_kg": "0.000",
            "rejected_kg": "80.000",
            "waste_reserved_kg": "0.000",
            "waste_consumed_kg": "0.000",
            "waste_available_kg": "0.000",
        }])

    def test_sending_a_rejected_lot_back_to_lab_testing_drops_rejected_kg(self):
        """Reverting a Rejected lot to Lab Testing clears its effective date
        and the rejected bucket drops to 0, same as the in_use revert.

        tests/test_inward_stock_api.py::InwardStockApiTest::test_sending_a_rejected_lot_back_to_lab_testing_drops_rejected_kg
        """
        self.login_as(self.seed_admin)
        created = self.client.post(
            "/api/sales-admin/inward-raw-materials",
            {
                "product": self.product1.public_id,
                "party": self.party.id,
                "lot_no": "SUP-2026-B7",
                "farmer_name": "Test Farmer",
                "quantity_kg": "500",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = f"/api/sales-admin/inward-raw-material/{created.data['public_id']}"

        lab_verdict(created.data["public_id"], "Fail", actor=self.seed_admin)

        counting = self.client.get(f"{RAW_STOCK_URL}?product={self.product1.public_id}")
        self.assertEqual(counting.data["lines"][0]["rejected_kg"], "500.000")

        reverted = self.client.patch(url, {"status": "Lab Testing"}, format="json")
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

    def test_other_stock_can_separate_balances_by_product_configuration(self):
        """tests/test_inward_stock_api.py::InwardStockApiTest::test_other_stock_can_separate_balances_by_product_configuration"""
        self.login_as(self.seed_admin)
        self._set_up_other_lots()
        product2_leaflet_recipe = OtherMaterialRecipe.objects.create(
            product=self.product2,
            material_type=self.leaflets,
            packet_weight=Decimal("1.000"),
            quantity=Decimal("1.000"),
            created_by=self.seed_admin,
        )
        InwardOtherMaterial.objects.create(
            recipe=product2_leaflet_recipe,
            party=self.party,
            quantity=Decimal("8"),
            effective_date=self.today,
            created_by=self.seed_admin,
        )

        response = self.client.get(f"{OTHER_STOCK_URL}?group_by=configuration")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["lines"], [
            {
                "product": {
                    "public_id": self.product1.public_id,
                    "name": self.product1.name,
                },
                "packet_weight": "1.000",
                "material_type": {"id": 3, "name": "leaflets", "unit_type": "count"},
                "on_hand": "6.000",
            },
            {
                "product": {
                    "public_id": self.product2.public_id,
                    "name": self.product2.name,
                },
                "packet_weight": "1.000",
                "material_type": {
                    "id": 1,
                    "name": "bag_outer_cover",
                    "unit_type": "kg",
                },
                "on_hand": "0.000",
            },
            {
                "product": {
                    "public_id": self.product2.public_id,
                    "name": self.product2.name,
                },
                "packet_weight": "1.000",
                "material_type": {
                    "id": 3,
                    "name": "leaflets",
                    "unit_type": "count",
                },
                "on_hand": "8.000",
            },
        ])
