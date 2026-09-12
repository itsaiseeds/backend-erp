"""API-level tests for the loose-stock endpoints.

Covers:
    POST  /api/sales-admin/update-loose-stock
    PATCH /api/sales-admin/update-loose-stock
    GET   /api/sales-admin/loose-stock

Loose stock is keyed by (product, packet_weight), so the payload is a list of
lines rather than a map keyed by one public id.

Run: tests/test_loose_stock_api.py::LooseStockApiTest
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from rest_framework import status

from aggregator.models import LooseStockSnapshot, ProductPackaging, Stage, StageIds
from authentication.models import Admin, User
from tests.common import WebApiTestCase

UPDATE_URL = "/api/sales-admin/update-loose-stock"
POSITION_URL = "/api/sales-admin/loose-stock"

SUPERUSER_PHONE = "9999999999"


class LooseStockApiTest(WebApiTestCase):
    """Tests for the loose-stock API endpoints.

    Run: tests/test_loose_stock_api.py::LooseStockApiTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(phone_number=SUPERUSER_PHONE)

        cls.stock_admin_user = User.objects.create_user(
            phone_number="8100000001", name="Stock Admin", created_by=cls.su,
            verified_by=cls.su, is_verified=True,
        )
        Admin.objects.create(
            user=cls.stock_admin_user, can_update_stock_count=True, created_by=cls.su
        )
        cls.plain_admin_user = User.objects.create_user(
            phone_number="8100000002", name="Plain Admin", created_by=cls.su,
            verified_by=cls.su, is_verified=True,
        )
        Admin.objects.create(
            user=cls.plain_admin_user, can_update_stock_count=False, created_by=cls.su
        )

        from aggregator.models import Crop

        cls.crop = Crop.objects.create(name="Bajra", created_by=cls.stock_admin_user)
        cls.product = cls.crop.products.create(
            name="Pearl Millet 88", stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("40.00"), created_by=cls.stock_admin_user,
        )
        # Two packagings at the SAME 1kg packet weight -> ONE loose pool.
        cls.pack_20 = ProductPackaging.objects.create(
            product=cls.product, packet_weight=Decimal("1.000"), packets=20,
            selling_price=Decimal("800.00"), created_by=cls.stock_admin_user,
        )
        cls.pack_30 = ProductPackaging.objects.create(
            product=cls.product, packet_weight=Decimal("1.000"), packets=30,
            selling_price=Decimal("1200.00"), created_by=cls.stock_admin_user,
        )
        cls.pack_half = ProductPackaging.objects.create(
            product=cls.product, packet_weight=Decimal("0.500"), packets=40,
            selling_price=Decimal("800.00"), created_by=cls.stock_admin_user,
        )

    # -- helpers ---------------------------------------------------------------

    def _stock_admin_request(self, method, url, **kwargs):
        self.login_as(self.stock_admin_user)
        return getattr(self.client, method)(url, **kwargs)

    def _line(self, weight="1.000", packets=12):
        return {
            "product": self.product.public_id,
            "packet_weight": weight,
            "packets": packets,
        }

    # -- permissions -----------------------------------------------------------

    def test_update_anonymous_rejected(self):
        """Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_update_anonymous_rejected"""
        resp = self.client.post(
            UPDATE_URL, data={"counts": [self._line()]}, format="json"
        )
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_admin_without_flag_cannot_update(self):
        """Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_admin_without_flag_cannot_update"""
        self.login_as(self.plain_admin_user)
        resp = self.client.post(
            UPDATE_URL, data={"counts": [self._line()]}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # -- writing ---------------------------------------------------------------

    def test_post_records_one_pool_per_product_and_weight(self):
        """Two packagings at the same weight share one pool, counted once.

        Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_post_records_one_pool_per_product_and_weight
        """
        resp = self._stock_admin_request(
            "post", UPDATE_URL, data={"counts": [self._line(packets=12)]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        one_kg = [
            r for r in resp.data
            if r["packet_weight"] == "1.000"
            and r["product"]["public_id"] == self.product.public_id
        ]
        self.assertEqual(len(one_kg), 1)
        self.assertEqual(one_kg[0]["packets"], 12)
        self.assertTrue(one_kg[0]["public_id"].startswith("LS-"))
        self.assertEqual(one_kg[0]["available"], 12)
        self.assertEqual(one_kg[0]["total_weight"], "12.000")

    def test_post_zero_fills_uncounted_pools(self):
        """Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_post_zero_fills_uncounted_pools"""
        resp = self._stock_admin_request(
            "post", UPDATE_URL, data={"counts": [self._line(packets=12)]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        half = next(
            r for r in resp.data
            if r["packet_weight"] == "0.500"
            and r["product"]["public_id"] == self.product.public_id
        )
        self.assertEqual(half["packets"], 0)

    def test_patch_leaves_other_pools_alone(self):
        """Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_patch_leaves_other_pools_alone"""
        self._stock_admin_request(
            "patch", UPDATE_URL,
            data={"counts": [self._line("1.000", 12), self._line("0.500", 7)]},
            format="json",
        )
        resp = self._stock_admin_request(
            "patch", UPDATE_URL, data={"counts": [self._line("1.000", 3)]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["packets"], 3)
        # The 0.500 pool was not named and must be untouched.
        half = LooseStockSnapshot.objects.get(
            product=self.product, packet_weight=Decimal("0.500")
        )
        self.assertEqual(half.packets, 7)

    # -- validation ------------------------------------------------------------

    def test_unknown_product_weight_pair_rejected(self):
        """A weight nothing is packed in is not a valid loose pool.

        Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_unknown_product_weight_pair_rejected
        """
        resp = self._stock_admin_request(
            "patch", UPDATE_URL, data={"counts": [self._line("2.500", 5)]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertEqual(LooseStockSnapshot.objects.count(), 0)

    def test_unknown_product_rejected(self):
        """Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_unknown_product_rejected"""
        resp = self._stock_admin_request(
            "patch", UPDATE_URL,
            data={
                "counts": [
                    {"product": "P-NONEXISTENT", "packet_weight": "1.000", "packets": 5}
                ]
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_duplicate_pair_in_one_payload_rejected(self):
        """The same pool named twice would let the last line silently win.

        Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_duplicate_pair_in_one_payload_rejected
        """
        resp = self._stock_admin_request(
            "patch", UPDATE_URL,
            data={"counts": [self._line("1.000", 12), self._line("1.000", 3)]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertEqual(LooseStockSnapshot.objects.count(), 0)

    def test_negative_packets_rejected(self):
        """Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_negative_packets_rejected"""
        resp = self._stock_admin_request(
            "patch", UPDATE_URL, data={"counts": [self._line("1.000", -1)]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    # -- reading ---------------------------------------------------------------

    def test_get_position_reports_pools_and_date(self):
        """Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_get_position_reports_pools_and_date"""
        self._stock_admin_request(
            "patch", UPDATE_URL, data={"counts": [self._line("1.000", 12)]},
            format="json",
        )
        resp = self._stock_admin_request("get", POSITION_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(
            resp.data["snapshot_date"], datetime.date.today().isoformat()
        )
        mine = next(
            line for line in resp.data["lines"]
            if line["product"]["public_id"] == self.product.public_id
        )
        self.assertEqual(mine["packet_weight"], "1.000")
        self.assertEqual(mine["on_hand"], 12)
        self.assertEqual(mine["available"], 12)

    def test_get_position_when_never_counted(self):
        """snapshot_date is null and the list is empty before any loose count.

        Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_get_position_when_never_counted
        """
        resp = self._stock_admin_request("get", POSITION_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertIsNone(resp.data["snapshot_date"])
        self.assertEqual(resp.data["lines"], [])

    def test_get_position_anonymous_rejected(self):
        """Run: tests/test_loose_stock_api.py::LooseStockApiTest::test_get_position_anonymous_rejected"""
        resp = self.client.get(POSITION_URL)
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
