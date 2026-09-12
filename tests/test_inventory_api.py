"""API-level tests for the inventory endpoints.

Covers:
    GET  /api/sales-admin/check-todays-inventory
    POST /api/sales-admin/update-todays-inventory
    PATCH /api/sales-admin/update-todays-inventory
    GET  /api/sales-admin/get-stock/<public_id>

Run: tests/test_inventory_api.py::InventoryApiTest
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from rest_framework import status

from aggregator.models import ProductPackaging, Stage, StageIds
from authentication.models import Admin, SalesPerson, User
from tests.common import WebApiTestCase

CHECK_URL = "/api/sales-admin/check-todays-inventory"
UPDATE_URL = "/api/sales-admin/update-todays-inventory"

SUPERUSER_PHONE = "9999999999"


class InventoryApiTest(WebApiTestCase):
    """Tests for the inventory API endpoints.

    Run: tests/test_inventory_api.py::InventoryApiTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(phone_number=SUPERUSER_PHONE)

        # -- users with different roles ----------------------------------------
        cls.stock_admin_user = User.objects.create_user(
            phone_number="8000000001",
            name="Stock Admin",
            created_by=cls.su,
            verified_by=cls.su,
            is_verified=True,
        )
        Admin.objects.create(
            user=cls.stock_admin_user,
            can_update_stock_count=True,
            created_by=cls.su,
        )

        cls.plain_admin_user = User.objects.create_user(
            phone_number="8000000002",
            name="Plain Admin",
            created_by=cls.su,
            verified_by=cls.su,
            is_verified=True,
        )
        Admin.objects.create(
            user=cls.plain_admin_user,
            can_update_stock_count=False,
            created_by=cls.su,
        )

        cls.salesperson_user = User.objects.create_user(
            phone_number="8000000003",
            name="Sales Person",
            created_by=cls.su,
            verified_by=cls.su,
            is_verified=True,
        )
        from aggregator.models import City, Country, Pincode, State

        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.su}
        )
        cls.state = State.objects.create(
            name="Maharashtra", country=cls.country, created_by=cls.su
        )
        cls.city = City.objects.create(
            name="Pune", state=cls.state, created_by=cls.su
        )
        cls.pincode = Pincode.objects.create(
            code="411001", city=cls.city, created_by=cls.su
        )
        SalesPerson.objects.create(
            user=cls.salesperson_user, city=cls.city, created_by=cls.su
        )

        # -- product data ------------------------------------------------------
        from aggregator.models import Crop

        cls.crop = Crop.objects.create(name="Wheat", created_by=cls.stock_admin_user)
        cls.product = cls.crop.products.create(
            name="PBW 725",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("55.50"),
            created_by=cls.stock_admin_user,
        )
        cls.pack1 = ProductPackaging.objects.create(
            product=cls.product,
            packet_weight=Decimal("0.500"),
            packets=50,
            selling_price=Decimal("2775.00"),
            created_by=cls.stock_admin_user,
        )
        cls.pack2 = ProductPackaging.objects.create(
            product=cls.product,
            packet_weight=Decimal("1.000"),
            packets=25,
            selling_price=Decimal("1387.50"),
            created_by=cls.stock_admin_user,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _stock_admin_request(self, method, url, **kwargs):
        self.login_as(self.stock_admin_user)
        return getattr(self.client, method)(url, **kwargs)

    def _plain_admin_request(self, method, url, **kwargs):
        self.login_as(self.plain_admin_user)
        return getattr(self.client, method)(url, **kwargs)

    # ------------------------------------------------------------------
    # GET check-todays-inventory
    # ------------------------------------------------------------------

    def test_check_inventory_no_snapshots(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_check_inventory_no_snapshots"""
        resp = self._stock_admin_request("get", CHECK_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_complete"])
        self.assertEqual(resp.data["snapshot_date"], datetime.date.today().isoformat())
        missing_ids = {m["public_id"] for m in resp.data["missing_packagings"]}
        self.assertIn(self.pack1.public_id, missing_ids)
        self.assertIn(self.pack2.public_id, missing_ids)

        # The same payload names who is allowed to do the counting: only admins
        # with can_update_stock_count=True.
        admin_phones = {a["phone_number"] for a in resp.data["stock_admins"]}
        self.assertIn(self.stock_admin_user.phone_number, admin_phones)
        self.assertNotIn(self.plain_admin_user.phone_number, admin_phones)

    def test_check_inventory_complete(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_check_inventory_complete"""
        from aggregator.InventoryOperations import record_stock_counts

        # Count every active packaging (the DB may have seed-data packagings
        # beyond the two we created in setUpTestData).
        counts = dict.fromkeys(ProductPackaging.objects.all(), 10)
        record_stock_counts(counts=counts, actor=self.stock_admin_user)
        resp = self._stock_admin_request("get", CHECK_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_complete"])
        self.assertEqual(resp.data["missing_packagings"], [])
        # is_complete covers bags only; loose was never counted.
        self.assertIsNone(resp.data["loose_snapshot_date"])

    def test_check_inventory_partial_count(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_check_inventory_partial_count"""
        from aggregator.InventoryOperations import record_stock_count

        record_stock_count(
            product_packaging=self.pack1,
            bags=10,
            actor=self.stock_admin_user,
        )
        resp = self._stock_admin_request("get", CHECK_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_complete"])
        missing_ids = {m["public_id"] for m in resp.data["missing_packagings"]}
        self.assertNotIn(self.pack1.public_id, missing_ids)
        self.assertIn(self.pack2.public_id, missing_ids)

    # ------------------------------------------------------------------
    # POST update-todays-inventory
    # ------------------------------------------------------------------

    def test_post_update_inventory_replaces_the_whole_day(self):
        """One POST writes a snapshot for every active packaging: the ones named in
        the payload get their count, the rest get zero, and the day is complete.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_replaces_the_whole_day
        """
        total_packagings = ProductPackaging.objects.count()
        resp = self._stock_admin_request(
            "post",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 20}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        # One snapshot per active packaging, not just the ones in the payload.
        self.assertIsInstance(resp.data, list)
        self.assertEqual(len(resp.data), total_packagings)

        snapshots = {snap["packaging"]["public_id"]: snap for snap in resp.data}
        counted = snapshots[self.pack1.public_id]
        self.assertTrue(counted["public_id"].startswith("INV-"))
        self.assertEqual(counted["snapshot_date"], datetime.date.today().isoformat())
        self.assertEqual(counted["bags"], 20)
        self.assertIn("packets_available", counted)
        # Bags only -- loose stock has its own endpoint and its own payload.
        self.assertNotIn("loose_packets", counted)
        self.assertNotIn("product_loose_packets_available", counted)

        # A packaging left out of the payload is zero-filled, not left uncounted.
        self.assertEqual(snapshots[self.pack2.public_id]["bags"], 0)

        # Everything now has a snapshot, so the day reads as complete.
        self.assertTrue(self._stock_admin_request("get", CHECK_URL).data["is_complete"])

    def test_a_count_needs_the_stock_permission_on_both_verbs(self):
        """``can_update_stock_count`` is a domain flag on ``Admin``, not a view flag,
        so it is checked here rather than in ``tests/test_view_contracts.py``.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_a_count_needs_the_stock_permission_on_both_verbs
        """
        for verb in ("post", "patch"):
            with self.subTest(verb=verb.upper()):
                resp = self._plain_admin_request(
                    verb,
                    UPDATE_URL,
                    data={"counts": {self.pack1.public_id: 10}},
                    format="json",
                )
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_count_payloads_are_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_invalid_count_payloads_are_rejected"""
        cases = [
            ("unknown packaging", {"PP-NONEXISTENT": 10}),
            ("negative count", {self.pack1.public_id: -5}),
            # The {bags, loose_packets} object form is gone: counts are bare ints.
            ("legacy object shape", {self.pack1.public_id: {"bags": 15, "loose_packets": 3}}),
        ]
        for label, counts in cases:
            with self.subTest(case=label):
                resp = self._stock_admin_request(
                    "post", UPDATE_URL, data={"counts": counts}, format="json"
                )
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_post_update_inventory_replaces_previous_day(self):
        """Recording today's count hard-deletes older-day rows.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_replaces_previous_day
        """
        from aggregator.InventoryOperations import record_stock_counts
        from aggregator.models import InventorySnapshot

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        record_stock_counts(
            counts={self.pack1: 5, self.pack2: 3},
            actor=self.stock_admin_user,
            snapshot_date=yesterday,
        )
        self.assertTrue(
            InventorySnapshot.all_objects.filter(snapshot_date=yesterday).exists()
        )

        # Now record today — yesterday's rows should be purged
        self._stock_admin_request(
            "post",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 10, self.pack2.public_id: 8}},
            format="json",
        )
        self.assertFalse(
            InventorySnapshot.all_objects.filter(snapshot_date=yesterday).exists()
        )

    # ------------------------------------------------------------------
    # PATCH update-todays-inventory
    # ------------------------------------------------------------------

    def test_patch_update_inventory_only_updates_named_packagings(self):
        """PATCH leaves unmentioned packagings untouched.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_patch_update_inventory_only_updates_named_packagings
        """
        from aggregator.InventoryOperations import record_stock_count

        # Seed pack1 with a count, leave pack2 uncounted
        record_stock_count(
            product_packaging=self.pack1,
            bags=5,
            actor=self.stock_admin_user,
        )

        # PATCH only pack2
        resp = self._stock_admin_request(
            "patch",
            UPDATE_URL,
            data={"counts": {self.pack2.public_id: 12}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertIsInstance(resp.data, list)
        # Only pack2 should be in the response (only the patched ones)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["packaging"]["public_id"], self.pack2.public_id)
        self.assertEqual(resp.data[0]["bags"], 12)

        # pack1 should still have its old count
        check_resp = self._stock_admin_request("get", CHECK_URL)
        self.assertFalse(check_resp.data["is_complete"])
        missing_ids = {m["public_id"] for m in check_resp.data["missing_packagings"]}
        self.assertNotIn(self.pack1.public_id, missing_ids)
        self.assertNotIn(self.pack2.public_id, missing_ids)

        # Re-patching a packaging that already has a count overwrites it.
        resp = self._stock_admin_request(
            "patch",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 20}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data[0]["bags"], 20)

    # ------------------------------------------------------------------
    # GET get-stock/<public_id>
    # ------------------------------------------------------------------

    def test_get_stock_packaging_returns_bag_pool(self):
        """PP- prefix returns the sealed-bag position.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_packaging_returns_bag_pool
        """
        from aggregator.InventoryOperations import record_stock_count

        url = f"/api/sales-admin/get-stock/{self.pack1.public_id}"

        # Before any snapshot exists, the position reads as empty rather than 404.
        empty = self._stock_admin_request("get", url)
        self.assertEqual(empty.status_code, status.HTTP_200_OK)
        self.assertEqual(empty.data["on_hand"], 0)
        self.assertEqual(empty.data["available"], 0)

        record_stock_count(product_packaging=self.pack1, bags=50, actor=self.stock_admin_user)

        resp = self._stock_admin_request("get", url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["public_id"], self.pack1.public_id)
        self.assertTrue(resp.data["name"].startswith(self.product.name))
        self.assertEqual(resp.data["on_hand"], 50)
        self.assertEqual(resp.data["reserved"], 0)
        self.assertEqual(resp.data["consumed"], 0)
        self.assertEqual(resp.data["available"], 50)

    def test_get_stock_product_returns_loose_pool_per_weight(self):
        """P- prefix returns the loose position broken down by packet weight.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_product_returns_loose_pool_per_weight
        """
        from aggregator.InventoryOperations import record_loose_stock

        record_loose_stock(
            product=self.product,
            packet_weight=Decimal("0.500"),
            packets=30,
            actor=self.stock_admin_user,
        )
        record_loose_stock(
            product=self.product,
            packet_weight=Decimal("1.000"),
            packets=10,
            actor=self.stock_admin_user,
        )
        resp = self._stock_admin_request(
            "get", f"/api/sales-admin/get-stock/{self.product.public_id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["public_id"], self.product.public_id)
        self.assertEqual(resp.data["name"], self.product.name)
        # One line per weight the product is packed in (0.500 and 1.000).
        by_weight = {line["packet_weight"]: line for line in resp.data["lines"]}
        self.assertEqual(set(by_weight), {"0.500", "1.000"})
        self.assertEqual(by_weight["0.500"]["on_hand"], 30)
        self.assertEqual(by_weight["0.500"]["available"], 30)
        self.assertEqual(by_weight["0.500"]["reserved"], 0)
        self.assertEqual(by_weight["0.500"]["consumed"], 0)
        # Each weight is its own pool: the one-kilo line reports its own 10
        # packets and is never added to, or filled from, the half-kilo pool.
        self.assertEqual(by_weight["1.000"]["on_hand"], 10)

    def test_get_stock_unknown_id_returns_404(self):
        """Both a known prefix with no row and an entirely unknown prefix 404.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_unknown_id_returns_404
        """
        for label, public_id in (
            ("known prefix, no such row", "PP-NONEXISTENT"),
            ("unknown prefix", "XX-123"),
        ):
            with self.subTest(case=label):
                resp = self._stock_admin_request(
                    "get", f"/api/sales-admin/get-stock/{public_id}"
                )
                self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

