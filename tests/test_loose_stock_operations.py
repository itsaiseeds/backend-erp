"""LooseStockSnapshot model + loose-pool operation tests.

Loose stock is stock in a packet but not in a bag, keyed by
``(product, packet_weight)``. The headline case here is the one this table
exists for: a product packed as both 1kg x 20 and 1kg x 30 has ONE pool of
loose 1kg packets, not two.

Also covers the independent date lifecycle -- the loose count is optional, is
never purged by a bag count, and is read at the latest *loose* date rather than
today.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from aggregator import InventoryOperations as inv
from aggregator.models import InventorySnapshot, LooseStockSnapshot, Stage, StageIds
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import Admin, User
from tests.common import DMLTestCase


class LooseStockTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.stock_admin = User.objects.create_user(
            "9400000001", "Stock Admin", created_by=cls.su, verified_by=cls.su,
            is_verified=True,
        )
        cls.plain_admin = User.objects.create_user(
            "9400000002", "Plain Admin", created_by=cls.su, verified_by=cls.su,
            is_verified=True,
        )
        cls.outsider = User.objects.create_user(
            "9400000003", "Outsider", created_by=cls.su, verified_by=cls.su,
            is_verified=True,
        )
        Admin.objects.create(
            user=cls.stock_admin, created_by=cls.su, can_update_stock_count=True
        )
        Admin.objects.create(
            user=cls.plain_admin, created_by=cls.su, can_update_stock_count=False
        )

        cls.product = create_product(
            name="Hybrid Maize", crop="Maize",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("90.00"), actor=cls.su,
        )
        # The P1/P2 case: same product, same 1kg packet, different bag sizes.
        cls.pack_20 = add_packaging(
            cls.product, packet_weight=Decimal("1.000"), packets=20, actor=cls.su
        )
        cls.pack_30 = add_packaging(
            cls.product, packet_weight=Decimal("1.000"), packets=30, actor=cls.su
        )
        # A second weight of the same product: a separate pool.
        cls.pack_half = add_packaging(
            cls.product, packet_weight=Decimal("0.500"), packets=40, actor=cls.su
        )
        cls.today = datetime.date.today()
        cls.w1 = Decimal("1.000")
        cls.whalf = Decimal("0.500")

    def _record(self, packets=12, *, weight=None, snapshot_date=None):
        return inv.record_loose_stock(
            product=self.product,
            packet_weight=weight or self.w1,
            packets=packets,
            actor=self.stock_admin,
            snapshot_date=snapshot_date,
        )

    # -- the model -------------------------------------------------------------

    def test_public_id_prefix_and_total_weight(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_public_id_prefix_and_total_weight"""
        snapshot = self._record(12)
        assert snapshot.public_id.startswith("LS-")
        assert snapshot.snapshot_date == self.today
        assert snapshot.total_weight == Decimal("12.000")

    def test_one_row_per_date_product_and_weight(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_one_row_per_date_product_and_weight"""
        self._record(12)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LooseStockSnapshot.objects.create(
                    snapshot_date=self.today,
                    product=self.product,
                    packet_weight=self.w1,
                    packets=5,
                    created_by=self.stock_admin,
                )

    def test_admin_without_flag_cannot_record(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_admin_without_flag_cannot_record"""
        with self.assertRaises(PermissionDenied):
            inv.record_loose_stock(
                product=self.product, packet_weight=self.w1, packets=5,
                actor=self.plain_admin,
            )

    def test_non_admin_cannot_record(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_non_admin_cannot_record"""
        with self.assertRaises(PermissionDenied):
            inv.record_loose_stock(
                product=self.product, packet_weight=self.w1, packets=5,
                actor=self.outsider,
            )

    def test_zero_weight_rejected(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_zero_weight_rejected"""
        with self.assertRaises(ValidationError):
            inv.record_loose_stock(
                product=self.product, packet_weight=Decimal("0.000"), packets=5,
                actor=self.stock_admin,
            )

    # -- the bug this table exists for ----------------------------------------

    def test_loose_pool_is_not_multiplied_by_packaging_count(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_loose_pool_is_not_multiplied_by_packaging_count"""
        # The product has TWO 1kg packagings (x20 and x30). 12 loose 1kg
        # packets is 12 -- the number of packagings is irrelevant to a packet
        # that is not in a bag.
        self._record(12)
        assert inv.on_hand_loose_packets(self.product, self.w1) == 12
        assert inv.available_loose_packets(self.product, self.w1) == 12

    def test_weights_are_separate_pools(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_weights_are_separate_pools"""
        self._record(12, weight=self.w1)
        self._record(7, weight=self.whalf)
        assert inv.on_hand_loose_packets(self.product, self.w1) == 12
        assert inv.on_hand_loose_packets(self.product, self.whalf) == 7

    def test_uncounted_pool_is_zero(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_uncounted_pool_is_zero"""
        self._record(12, weight=self.w1)
        assert inv.on_hand_loose_packets(self.product, self.whalf) == 0

    def test_product_loose_weights_lists_packed_weights(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_product_loose_weights_lists_packed_weights"""
        # Two 1kg packagings collapse to one weight.
        assert list(inv.product_loose_weights(self.product)) == [self.whalf, self.w1]

    # -- writing ---------------------------------------------------------------

    def test_recount_overwrites_rather_than_duplicating(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_recount_overwrites_rather_than_duplicating"""
        self._record(12)
        self._record(9)
        rows = LooseStockSnapshot.objects.filter(
            snapshot_date=self.today, product=self.product, packet_weight=self.w1
        )
        assert rows.count() == 1
        assert rows.first().packets == 9

    def test_newer_loose_count_purges_older_loose_days(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_newer_loose_count_purges_older_loose_days"""
        yesterday = self.today - datetime.timedelta(days=1)
        self._record(50, snapshot_date=yesterday)
        self._record(12)
        assert LooseStockSnapshot.all_objects.filter(snapshot_date=yesterday).count() == 0
        assert inv.on_hand_loose_packets(self.product, self.w1) == 12

    # -- the two lifecycles are independent ------------------------------------

    def test_a_new_days_bag_count_does_not_purge_loose_stock(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_a_new_days_bag_count_does_not_purge_loose_stock"""
        yesterday = self.today - datetime.timedelta(days=1)
        self._record(12, snapshot_date=yesterday)
        # A bag count for today must not touch yesterday's still-valid loose count.
        inv.record_stock_count(
            product_packaging=self.pack_20, bags=400, actor=self.stock_admin
        )
        assert LooseStockSnapshot.objects.filter(snapshot_date=yesterday).count() == 1
        assert inv.on_hand_loose_packets(self.product, self.w1) == 12

    def test_a_loose_count_does_not_purge_bag_snapshots(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_a_loose_count_does_not_purge_bag_snapshots"""
        yesterday = self.today - datetime.timedelta(days=1)
        inv.record_stock_count(
            product_packaging=self.pack_20, bags=400, actor=self.stock_admin,
            snapshot_date=yesterday,
        )
        self._record(12)
        assert InventorySnapshot.objects.filter(snapshot_date=yesterday).count() == 1

    def test_loose_reads_use_the_latest_loose_date_not_today(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_loose_reads_use_the_latest_loose_date_not_today"""
        # A count taken three days ago is still the truth: nothing forces a
        # daily loose count, so reads must not silently fall back to zero.
        old = self.today - datetime.timedelta(days=3)
        self._record(12, snapshot_date=old)
        assert inv.latest_loose_snapshot_date() == old
        assert inv.loose_date() == old
        assert inv.on_hand_loose_packets(self.product, self.w1) == 12

    def test_loose_date_falls_back_to_today_when_never_counted(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_loose_date_falls_back_to_today_when_never_counted"""
        assert inv.latest_loose_snapshot_date() is None
        assert inv.loose_date() == self.today
        assert inv.on_hand_loose_packets(self.product, self.w1) == 0

    def test_loose_count_is_excluded_from_the_completeness_gate(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_loose_count_is_excluded_from_the_completeness_gate"""
        from aggregator.models import ProductPackaging

        # Count every bag and no loose stock at all: the day is still complete.
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), 10),
            actor=self.stock_admin,
        )
        assert LooseStockSnapshot.objects.count() == 0
        assert inv.is_stock_count_complete() is True

    # -- payload shapes --------------------------------------------------------

    def test_position_and_payload_shapes(self):
        """tests/test_loose_stock_operations.py::LooseStockTest::test_position_and_payload_shapes"""
        snapshot = self._record(12)

        position = inv.loose_stock_position()
        mine = next(e for e in position if e["product"] == self.product)
        assert mine["packet_weight"] == self.w1
        assert mine["packets_on_hand"] == 12
        assert mine["packets_available"] == 12

        payload = inv.loose_stock_payload(snapshot)
        assert "id" not in payload
        assert payload["public_id"].startswith("LS-")
        assert payload["product"]["public_id"] == self.product.public_id
        assert payload["packet_weight"] == "1.000"
        assert payload["packets"] == 12
        assert payload["available"] == 12
