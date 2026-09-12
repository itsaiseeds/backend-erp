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

    def test_check_inventory_anonymous_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_check_inventory_anonymous_rejected"""
        resp = self.client.get(CHECK_URL)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_check_inventory_non_admin_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_check_inventory_non_admin_rejected"""
        self.login_as(self.salesperson_user)
        resp = self.client.get(CHECK_URL)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_check_inventory_no_snapshots(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_check_inventory_no_snapshots"""
        resp = self._stock_admin_request("get", CHECK_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_complete"])
        self.assertEqual(resp.data["snapshot_date"], datetime.date.today().isoformat())
        missing_ids = {m["public_id"] for m in resp.data["missing_packagings"]}
        self.assertIn(self.pack1.public_id, missing_ids)
        self.assertIn(self.pack2.public_id, missing_ids)

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

    def test_check_inventory_returns_stock_admins(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_check_inventory_returns_stock_admins"""
        resp = self._stock_admin_request("get", CHECK_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        admins = resp.data["stock_admins"]
        admin_phones = {a["phone_number"] for a in admins}
        # stock_admin_user has can_update_stock_count=True
        self.assertIn(self.stock_admin_user.phone_number, admin_phones)
        # plain_admin_user has can_update_stock_count=False — should not appear
        self.assertNotIn(self.plain_admin_user.phone_number, admin_phones)

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

    def test_post_update_inventory_anonymous_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_anonymous_rejected"""
        resp = self.client.post(
            UPDATE_URL,
            {"counts": {self.pack1.public_id: 10}},
            format="json",
        )
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_post_update_inventory_non_admin_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_non_admin_rejected"""
        self.login_as(self.salesperson_user)
        resp = self.client.post(
            UPDATE_URL,
            {"counts": {self.pack1.public_id: 10}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_update_inventory_admin_without_stock_permission_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_admin_without_stock_permission_rejected"""
        resp = self._plain_admin_request(
            "post",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 10}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_update_inventory_creates_all_packagings(self):
        """POST replaces entire day: missing packagings get 0.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_creates_all_packagings
        """
        total_packagings = ProductPackaging.objects.count()
        resp = self._stock_admin_request(
            "post",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 15}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        # Response is a list of all snapshots — one per active packaging
        self.assertIsInstance(resp.data, list)
        self.assertEqual(len(resp.data), total_packagings)
        # All packagings should now have snapshots — inventory is complete
        check_resp = self._stock_admin_request("get", CHECK_URL)
        self.assertTrue(check_resp.data["is_complete"])

    def test_post_update_inventory_zero_fills_missing(self):
        """Packagings not in the payload get bags=0.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_zero_fills_missing
        """
        resp = self._stock_admin_request(
            "post",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 10}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        # Find the snapshot for pack2 — should be 0 bags
        pack2_snap = next(
            s for s in resp.data if s["packaging"]["public_id"] == self.pack2.public_id
        )
        self.assertEqual(pack2_snap["bags"], 0)

    def test_post_update_inventory_snapshot_shape(self):
        """Each snapshot has the expected fields.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_snapshot_shape
        """
        resp = self._stock_admin_request(
            "post",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 20}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        snap = next(
            s for s in resp.data if s["packaging"]["public_id"] == self.pack1.public_id
        )
        self.assertTrue(snap["public_id"].startswith("INV-"))
        self.assertEqual(snap["snapshot_date"], datetime.date.today().isoformat())
        self.assertEqual(snap["bags"], 20)
        self.assertIn("packets_available", snap)
        # Bags only -- loose stock has its own endpoint and its own payload.
        self.assertNotIn("loose_packets", snap)
        self.assertNotIn("product_loose_packets_available", snap)

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

    def test_post_update_inventory_unknown_packaging_rejected(self):
        """A nonexistent public_id in counts should be rejected.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_unknown_packaging_rejected
        """
        resp = self._stock_admin_request(
            "post",
            UPDATE_URL,
            data={"counts": {"PP-NONEXISTENT": 10}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_update_inventory_negative_count_rejected(self):
        """Negative bag counts should be rejected.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_post_update_inventory_negative_count_rejected
        """
        resp = self._stock_admin_request(
            "post",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: -5}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # PATCH update-todays-inventory
    # ------------------------------------------------------------------

    def test_patch_update_inventory_admin_without_stock_permission_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_patch_update_inventory_admin_without_stock_permission_rejected"""
        resp = self._plain_admin_request(
            "patch",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 10}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

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

    def test_patch_update_inventory_updates_existing_count(self):
        """PATCH overwrites an existing count for the same packaging.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_patch_update_inventory_updates_existing_count
        """
        from aggregator.InventoryOperations import record_stock_count

        record_stock_count(
            product_packaging=self.pack1,
            bags=5,
            actor=self.stock_admin_user,
        )

        resp = self._stock_admin_request(
            "patch",
            UPDATE_URL,
            data={"counts": {self.pack1.public_id: 20}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data[0]["bags"], 20)

    def test_update_inventory_rejects_the_old_object_count_shape(self):
        """The {bags, loose_packets} object form is gone: counts are bare ints.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_update_inventory_rejects_the_old_object_count_shape
        """
        resp = self._stock_admin_request(
            "patch",
            UPDATE_URL,
            data={
                "counts": {
                    self.pack1.public_id: {"bags": 15, "loose_packets": 3},
                }
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    # ------------------------------------------------------------------
    # GET get-stock/<public_id>
    # ------------------------------------------------------------------

    def test_get_stock_anonymous_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_anonymous_rejected"""
        resp = self.client.get(f"/api/sales-admin/get-stock/{self.pack1.public_id}")
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_get_stock_non_admin_rejected(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_non_admin_rejected"""
        self.login_as(self.salesperson_user)
        resp = self.client.get(f"/api/sales-admin/get-stock/{self.pack1.public_id}")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_stock_packaging_returns_bag_pool(self):
        """PP- prefix returns the sealed-bag position.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_packaging_returns_bag_pool
        """
        from aggregator.InventoryOperations import record_stock_count

        record_stock_count(
            product_packaging=self.pack1,
            bags=50,
            actor=self.stock_admin_user,
        )
        resp = self._stock_admin_request(
            "get", f"/api/sales-admin/get-stock/{self.pack1.public_id}"
        )
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
        # The other weight was never counted, so it is empty -- not 30.
        self.assertEqual(by_weight["1.000"]["on_hand"], 0)

    def test_get_stock_unknown_id_returns_404(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_unknown_id_returns_404"""
        resp = self._stock_admin_request("get", "/api/sales-admin/get-stock/PP-NONEXISTENT")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_stock_unknown_prefix_returns_404(self):
        """Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_unknown_prefix_returns_404"""
        resp = self._stock_admin_request("get", "/api/sales-admin/get-stock/XX-123")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_stock_no_snapshot_defaults_to_zero(self):
        """Without a snapshot, on_hand and available are 0.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_no_snapshot_defaults_to_zero
        """
        resp = self._stock_admin_request(
            "get", f"/api/sales-admin/get-stock/{self.pack1.public_id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["on_hand"], 0)
        self.assertEqual(resp.data["available"], 0)

    def test_get_stock_loose_never_sums_across_weights(self):
        """Each packet weight is its own pool -- weights are never added together.

        Run: tests/test_inventory_api.py::InventoryApiTest::test_get_stock_loose_never_sums_across_weights
        """
        from aggregator.InventoryOperations import record_loose_stock

        record_loose_stock(
            product=self.product, packet_weight=Decimal("0.500"), packets=20,
            actor=self.stock_admin_user,
        )
        record_loose_stock(
            product=self.product, packet_weight=Decimal("1.000"), packets=10,
            actor=self.stock_admin_user,
        )
        resp = self._stock_admin_request(
            "get", f"/api/sales-admin/get-stock/{self.product.public_id}"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        by_weight = {line["packet_weight"]: line for line in resp.data["lines"]}
        # 20 half-kilo packets and 10 one-kilo packets, reported separately.
        self.assertEqual(by_weight["0.500"]["on_hand"], 20)
        self.assertEqual(by_weight["1.000"]["on_hand"], 10)
