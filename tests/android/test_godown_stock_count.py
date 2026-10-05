"""ORM-backed tests for the godown-manager stock-count endpoints.

Covers what the ``godown/...`` count endpoints *do* from the app: the
packaging list the count is keyed by, the readiness report, the sealed-bag
count (POST/PATCH), the loose-packet count (POST/PATCH) and the interleaved
export. Who may call them is owned by ``tests/test_view_contracts.py``; the
counting rules themselves are proven by the web inventory tests -- here we show
the Android endpoints reach the same ``InventoryOperations`` writes.

``stock_ledger_guard`` is left **on**: every count in this module is written
through the API, so the stock ledger must reconcile with the live figures once
each test ends (``DMLTestCase._assert_stock_ledger_in_sync``).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from rest_framework import status

from aggregator.models import (
    Crop,
    InventorySnapshot,
    LooseStockSnapshot,
    ProductPackaging,
    Stage,
    StageIds,
)
from aggregator.ProductOperations import usable_packagings
from authentication.models import Admin, GodownManager, User
from tests.android.common import AndroidApiTestCase
from tests.common import book_raw_material_for_every_product

BASE = "/android/api/v1/godown/"
CHECK_URL = BASE + "check-todays-inventory"
BAGS_URL = BASE + "update-bag-stock"
LOOSE_URL = BASE + "update-sample-packet-stock"
EXPORT_URL = BASE + "export/inventory-snapshots"
PACKAGINGS_URL = BASE + "product-packagings"


def _keys(value) -> set[str]:
    """Every dict key anywhere inside ``value``."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for item in value for k in _keys(item)}
    return set()


class GodownStockCountApiTest(AndroidApiTestCase):
    """Daily bag and loose counts, the readiness report and the count export.

    tests/android/test_godown_stock_count.py::GodownStockCountApiTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")

        def make_user(phone: str, name: str) -> User:
            return User.objects.create_user(
                phone_number=phone,
                name=name,
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            )

        cls.manager = GodownManager.objects.create(
            user=make_user("7000000011", "godown counter"),
            created_by=cls.superuser,
        )
        cls.stock_admin_user = make_user("7000000012", "stock admin")
        Admin.objects.create(
            user=cls.stock_admin_user,
            can_update_stock_count=True,
            created_by=cls.superuser,
        )

        cls.crop = Crop.objects.create(name="Godown Wheat", created_by=cls.manager.user)
        cls.product = cls.crop.products.create(
            name="Godown PBW 725",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("55.50"),
            created_by=cls.manager.user,
        )
        cls.half_kg = ProductPackaging.objects.create(
            product=cls.product,
            packet_weight=Decimal("0.500"),
            packets=50,
            selling_price=Decimal("2775.00"),
            created_by=cls.manager.user,
        )
        cls.one_kg = ProductPackaging.objects.create(
            product=cls.product,
            packet_weight=Decimal("1.000"),
            packets=25,
            selling_price=Decimal("1387.50"),
            created_by=cls.manager.user,
        )
        # Counts are checked against the raw material packed out, for every
        # product (a POST counts every active packaging, seeded ones included).
        book_raw_material_for_every_product(actor=cls.manager.user)

    def setUp(self):
        super().setUp()
        self.login_as(self.manager.user)

    def _post_bags(self, counts: dict[str, int]):
        return self.client.post(BAGS_URL, {"counts": counts}, format="json")

    def _patch_bags(self, counts: dict[str, int]):
        return self.client.patch(BAGS_URL, {"counts": counts}, format="json")

    def _loose_lines(self, **weights) -> list[dict]:
        return [
            {"product": self.product.public_id, "packet_weight": weight, "packets": packets}
            for weight, packets in weights.items()
        ]

    # -- the counter's picker ---------------------------------------------------

    def test_the_packaging_list_is_exactly_what_the_count_accepts(self):
        """The rows are the packagings ``update-bag-stock`` takes, each labelled
        with its product image, and a frozen product's drop out of the list just
        as they are refused by the count.

        tests/android/test_godown_stock_count.py::GodownStockCountApiTest::test_the_packaging_list_is_exactly_what_the_count_accepts
        """
        self.product.image_url = "/media/products/godown-pbw-725.jpg"
        self.product.save(update_fields=["image_url"])

        resp = self.client.get(PACKAGINGS_URL)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        listed = {row["public_id"]: row for row in resp.data}
        self.assertLessEqual({self.half_kg.public_id, self.one_kg.public_id}, set(listed))
        row = listed[self.half_kg.public_id]
        self.assertEqual(row["product"]["public_id"], self.product.public_id)
        self.assertTrue(row["product"]["is_usable"])
        # The picture comes with the row: no second lookup to label a bag.
        self.assertEqual(row["product"]["image_url"], "/media/products/godown-pbw-725.jpg")
        self.assertEqual(row["packets"], 50)
        self.assertEqual(float(row["total_weight"]), 25.0)
        self.assertNotIn("id", row)

        # The public_ids handed out are the keys the count takes.
        counted = self._patch_bags({self.half_kg.public_id: 3})
        self.assertEqual(counted.status_code, status.HTTP_200_OK, counted.data)

        self.product.is_usable = False
        self.product.save(update_fields=["is_usable"])
        default_ids = {r["public_id"] for r in self.client.get(PACKAGINGS_URL).data}
        self.assertNotIn(self.half_kg.public_id, default_ids)
        frozen_ids = {
            r["public_id"]
            for r in self.client.get(PACKAGINGS_URL, {"is_usable": "false"}).data
        }
        self.assertIn(self.half_kg.public_id, frozen_ids)

    # -- counting ---------------------------------------------------------------

    def test_a_godown_manager_counts_the_day_without_an_admin_profile(self):
        """POST replaces the whole day and the count is the manager's own.

        The godown role itself grants ``can_update_stock_count``, so the
        manager needs no ``Admin`` profile to count -- the point of the endpoint.

        tests/android/test_godown_stock_count.py::GodownStockCountApiTest::test_a_godown_manager_counts_the_day_without_an_admin_profile
        """
        self.assertFalse(self.manager.user.is_admin_user)
        self.assertFalse(self.client.get(CHECK_URL).data["is_complete"])

        resp = self._post_bags({self.half_kg.public_id: 20})

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        snapshots = {row["packaging"]["public_id"]: row for row in resp.data}
        self.assertEqual(len(resp.data), usable_packagings().count())
        self.assertEqual(snapshots[self.half_kg.public_id]["bags"], 20)
        # A packaging the payload left out is zero-filled, not left uncounted.
        self.assertEqual(snapshots[self.one_kg.public_id]["bags"], 0)

        written = InventorySnapshot.objects.get(
            snapshot_date=date.today(), product_packaging=self.half_kg
        )
        self.assertEqual(written.created_by, self.manager.user)
        self.assertEqual(written.bags, 20)

        self.assertTrue(self.client.get(CHECK_URL).data["is_complete"])

    def test_a_partial_count_touches_only_the_packaging_it_names(self):
        """PATCH leaves every other packaging of the day as it was.

        tests/android/test_godown_stock_count.py::GodownStockCountApiTest::test_a_partial_count_touches_only_the_packaging_it_names
        """
        resp = self._patch_bags({self.one_kg.public_id: 12})

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["packaging"]["public_id"], self.one_kg.public_id)
        self.assertEqual(resp.data[0]["bags"], 12)
        # One packaging of many is not a counted day.
        self.assertFalse(self.client.get(CHECK_URL).data["is_complete"])
        self.assertFalse(InventorySnapshot.objects.filter(product_packaging=self.half_kg).exists())

        again = self._patch_bags({self.half_kg.public_id: 5})
        self.assertEqual(again.status_code, status.HTTP_200_OK, again.data)
        self.assertEqual(InventorySnapshot.objects.get(product_packaging=self.one_kg).bags, 12)

    def test_the_readiness_report_names_the_admins_who_may_upload_the_count(self):
        """``stock_admins`` is the opted-in admin list; the manager is not on it.

        tests/android/test_godown_stock_count.py::GodownStockCountApiTest::test_the_readiness_report_names_the_admins_who_may_upload_the_count
        """
        resp = self.client.get(CHECK_URL)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        phones = {row["phone_number"] for row in resp.data["stock_admins"]}
        self.assertIn(self.stock_admin_user.phone_number, phones)
        self.assertNotIn(self.manager.user.phone_number, phones)

    def test_a_count_beyond_the_booked_raw_material_is_refused(self):
        """The shared raw-material guard bites from the app as well (400).

        tests/android/test_godown_stock_count.py::GodownStockCountApiTest::test_a_count_beyond_the_booked_raw_material_is_refused
        """
        # 0.5kg x 50 packets = 25kg a bag; 50,000 bags needs 1,250,000kg of the
        # 1,000,000kg booked for this product.
        resp = self._post_bags({self.half_kg.public_id: 50000})

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)
        self.assertIn("raw material", resp.data["detail"].lower())
        self.assertFalse(InventorySnapshot.objects.filter(product_packaging=self.half_kg).exists())

    # -- loose packets ----------------------------------------------------------

    def test_loose_packets_are_their_own_lines_and_leave_the_bag_count_alone(self):
        """Loose stock is keyed by (product, packet_weight) on its own lifecycle.

        tests/android/test_godown_stock_count.py::GodownStockCountApiTest::test_loose_packets_are_their_own_lines_and_leave_the_bag_count_alone
        """
        resp = self.client.post(
            LOOSE_URL,
            {"counts": self._loose_lines(**{"0.500": 5, "1.000": 7})},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        lines = {(row["product"]["public_id"], row["packet_weight"]): row for row in resp.data}
        half = lines[(self.product.public_id, "0.500")]
        self.assertEqual(half["packets"], 5)
        self.assertEqual(half["total_weight"], "2.500")
        self.assertEqual(lines[(self.product.public_id, "1.000")]["packets"], 7)

        written = LooseStockSnapshot.objects.get(
            snapshot_date=date.today(),
            product=self.product,
            packet_weight=Decimal("0.500"),
        )
        self.assertEqual(written.created_by, self.manager.user)
        # The sealed-bag pool is untouched: no bag row exists for today yet.
        self.assertFalse(InventorySnapshot.objects.filter(snapshot_date=date.today()).exists())

        patched = self.client.patch(
            LOOSE_URL,
            {"counts": self._loose_lines(**{"0.500": 9})},
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.data)
        self.assertEqual(len(patched.data), 1)
        self.assertEqual(patched.data[0]["packets"], 9)
        self.assertEqual(
            LooseStockSnapshot.objects.get(
                product=self.product, packet_weight=Decimal("1.000")
            ).packets,
            7,
        )

    # -- export -----------------------------------------------------------------

    def test_the_export_interleaves_both_pools_and_rejects_a_half_window(self):
        """Both pools come back in one flat page; a half-given window is a 400.

        tests/android/test_godown_stock_count.py::GodownStockCountApiTest::test_the_export_interleaves_both_pools_and_rejects_a_half_window
        """
        self._post_bags({self.half_kg.public_id: 20, self.one_kg.public_id: 10})
        self.client.patch(
            LOOSE_URL,
            {"counts": self._loose_lines(**{"0.500": 5})},
            format="json",
        )

        resp = self.client.get(EXPORT_URL)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["total_count"], len(resp.data["results"]))
        for key in ("total_pages", "next_page_number", "previous_page_number"):
            self.assertIn(key, resp.data)

        rows = [
            row
            for row in resp.data["results"]
            if row.get("packaging", {}).get("product", {}).get("public_id")
            == self.product.public_id
            or row.get("product", {}).get("public_id") == self.product.public_id
        ]
        kinds = [row["kind"] for row in rows]
        self.assertEqual(kinds, ["bag", "bag", "loose"])
        self.assertEqual(sorted(row["bags"] for row in rows if row["kind"] == "bag"), [10, 20])
        self.assertEqual([row["packets"] for row in rows if row["kind"] == "loose"], [5])
        # Counted figures only, never the live position.
        self.assertFalse(_keys(rows) & {"packets_available", "reserved", "consumed", "available"})

        half_window = self.client.get(EXPORT_URL, {"start_date": date.today().isoformat()})
        self.assertEqual(half_window.status_code, status.HTTP_400_BAD_REQUEST, half_window.data)
