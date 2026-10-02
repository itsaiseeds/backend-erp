"""Count carry-forward: a partial count that opens a new day must not zero the rest.

``PATCH update-bag-stock`` / ``update-sample-packet-stock`` can open a new date
naming only some pools. Before carry-forward every unnamed pool then read 0 on
hand at the latest date, silently "returning" its raw and packing material and
sending availability negative. Now every pool counted on the previous latest
date that the write does not name is counted onto the new date at its physical
figure (last count minus what was dispatched since), and the ledger records it
as ``STOCK_COUNTED / CARRIED_FORWARD``.

Run: bash scripts/run.sh test-serial tests/test_stock_count_carry_forward.py
"""

from __future__ import annotations

import datetime

from aggregator import InventoryOperations as inv
from authentication.models import Admin, User
from tests.common import WebApiTestCase
from tests.stock_ledger_support import TODAY, W1, LedgerWorldTestCase

TOMORROW = TODAY + datetime.timedelta(days=1)


class StockCountCarryForwardTest(LedgerWorldTestCase):
    def setUp(self):
        super().setUp()
        self.raw(self.product, "100000")
        self.raw(self.other_product, "100000")
        self.pouches("100000")
        self.count_everything({self.pp1: 50, self.qq1: 30})
        self.count_loose(self.other_product, 40)
        # Q ships 3 bags and 5 loose packets on day one, after the count.
        order = self.order(self.qq1, 3)
        self.dispatch(order, self.qq1)
        loose = self.custom_order(self.other_product, 5)
        self.dispatch_custom(loose, self.other_product)

    def test_a_partial_bag_count_on_a_new_day_carries_the_unnamed_pools(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardTest::test_a_partial_bag_count_on_a_new_day_carries_the_unnamed_pools"""
        available = inv.available_bags(self.qq1)
        raw_before = inv.raw_available_kg(self.other_product)
        mark = self.marker()

        self.count_bags({self.pp1: 40}, day=TOMORROW, carry_forward=True)

        # Q was not named, yet reads its physical figure on the new day: 30 - 3.
        self.assertEqual(inv.on_hand_bags(self.qq1, TOMORROW), 27)
        self.assertEqual(inv.available_bags(self.qq1, TOMORROW), available)
        self.assertEqual(inv.raw_available_kg(self.other_product), raw_before)
        kinds = self.kinds_since(mark, self.other_product)
        self.assertEqual(kinds, [("STOCK_COUNTED", "CARRIED_FORWARD")])

    def test_without_carry_forward_the_unnamed_pool_reads_zero(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardTest::test_without_carry_forward_the_unnamed_pool_reads_zero"""
        self.count_bags({self.pp1: 40}, day=TOMORROW)
        self.assertEqual(inv.on_hand_bags(self.qq1, TOMORROW), 0)

    def test_a_full_count_names_every_packaging_so_unnamed_ones_are_an_explicit_zero(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardTest::test_a_full_count_names_every_packaging_so_unnamed_ones_are_an_explicit_zero"""
        self.count_everything({self.pp1: 40}, day=TOMORROW)
        self.assertEqual(inv.on_hand_bags(self.qq1, TOMORROW), 0)

    def test_a_partial_loose_count_on_a_new_day_carries_the_unnamed_pools(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardTest::test_a_partial_loose_count_on_a_new_day_carries_the_unnamed_pools"""
        available = inv.available_loose_packets(self.other_product, W1)
        raw_before = inv.raw_available_kg(self.other_product)
        mark = self.marker()

        self.count_loose(self.product, 10, day=TOMORROW, carry_forward=True)

        self.assertEqual(inv.on_hand_loose_packets(self.other_product, W1, TOMORROW), 35)
        self.assertEqual(
            inv.available_loose_packets(self.other_product, W1, TOMORROW), available
        )
        self.assertEqual(inv.raw_available_kg(self.other_product), raw_before)
        self.assertIn(
            ("STOCK_COUNTED", "CARRIED_FORWARD"),
            self.kinds_since(mark, self.other_product),
        )

    def test_a_carried_pool_is_labelled_per_product_when_two_products_share_a_weight(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardTest::test_a_carried_pool_is_labelled_per_product_when_two_products_share_a_weight"""
        self.count_loose(self.product, 10)
        loose = self.custom_order(self.product, 4)
        self.dispatch_custom(loose, self.product)
        mark = self.marker()

        # Q is counted; P (same 1kg weight) is only carried forward.
        self.count_loose(self.other_product, 30, day=TOMORROW, carry_forward=True)

        self.assertEqual(
            self.kinds_since(mark, self.product), [("STOCK_COUNTED", "CARRIED_FORWARD")]
        )
        self.assertEqual(
            self.kinds_since(mark, self.other_product), [("STOCK_ADJUSTED", "LOOSE_COUNT")]
        )

    def test_a_count_on_the_same_day_carries_nothing(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardTest::test_a_count_on_the_same_day_carries_nothing"""
        mark = self.marker()
        self.count_bags({self.pp1: 40}, carry_forward=True)
        self.assertEqual(self.kinds_since(mark, self.other_product), [])
        self.assertEqual(inv.on_hand_bags(self.qq1), 30)


class StockCountCarryForwardApiTest(LedgerWorldTestCase, WebApiTestCase):
    """The PATCH endpoints carry unnamed pools forward; the POST endpoints do not.

    The counts of "yesterday" are written through the operations layer (the API
    only counts today), then today's PATCH / POST is made over HTTP.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.app_admin = User.objects.create_user(
            "9530000001", "Carry Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        Admin.objects.create(user=cls.app_admin, created_by=cls.su, can_update_stock_count=True)

    def setUp(self):
        super().setUp()
        self.login_as(self.app_admin)
        self.raw(self.product, "100000")
        self.raw(self.other_product, "100000")
        self.pouches("100000")
        yesterday = TODAY - datetime.timedelta(days=1)
        self.count_everything({self.pp1: 50, self.qq1: 30}, day=yesterday)
        self.count_loose(self.other_product, 40, day=yesterday)

    def test_patch_update_bag_stock_carries_the_unnamed_packagings(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardApiTest::test_patch_update_bag_stock_carries_the_unnamed_packagings"""
        response = self.client.patch(
            "/api/sales-admin/update-bag-stock",
            {"counts": {self.pp1.public_id: 40}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(inv.on_hand_bags(self.qq1, TODAY), 30)
        self.assertTrue(inv.is_stock_count_complete(TODAY))

    def test_patch_update_sample_packet_stock_carries_the_unnamed_pools(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardApiTest::test_patch_update_sample_packet_stock_carries_the_unnamed_pools"""
        response = self.client.patch(
            "/api/sales-admin/update-sample-packet-stock",
            {"counts": [{"product": self.product.public_id, "packet_weight": "1.000", "packets": 5}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(inv.on_hand_loose_packets(self.other_product, W1, TODAY), 40)

    def test_post_update_bag_stock_zeroes_the_unnamed_packagings(self):
        """tests/test_stock_count_carry_forward.py::StockCountCarryForwardApiTest::test_post_update_bag_stock_zeroes_the_unnamed_packagings"""
        response = self.client.post(
            "/api/sales-admin/update-bag-stock",
            {"counts": {self.pp1.public_id: 40}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(inv.on_hand_bags(self.qq1, TODAY), 0)
