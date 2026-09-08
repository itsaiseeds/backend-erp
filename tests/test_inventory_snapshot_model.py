"""InventorySnapshot model tests.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError

from aggregator.models import InventorySnapshot
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import Admin, User
from tests.common import DMLTestCase


class InventorySnapshotModelTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.stock_admin_user = User.objects.create_user(
            "9100000001", "Stock Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.plain_admin_user = User.objects.create_user(
            "9100000002", "Plain Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.outsider = User.objects.create_user(
            "9100000003", "Outsider", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        Admin.objects.create(
            user=cls.stock_admin_user, created_by=cls.su, can_update_stock_count=True
        )
        Admin.objects.create(
            user=cls.plain_admin_user, created_by=cls.su, can_update_stock_count=False
        )

        cls.product = create_product(
            name="Hybrid Bajra", crop="Bajra",
            buying_price=Decimal("100.00"), selling_price=Decimal("150.00"), actor=cls.su,
        )
        cls.pack = add_packaging(
            cls.product, packet_weight=Decimal("1.000"), packets=40, actor=cls.su
        )
        cls.today = datetime.date.today()

    def _snapshot(self, *, bags=400, actor=None, **kwargs):
        return InventorySnapshot(
            snapshot_date=kwargs.pop("snapshot_date", self.today),
            product_packaging=kwargs.pop("product_packaging", self.pack),
            bags=bags,
            created_by=actor or self.stock_admin_user,
            **kwargs,
        )

    def test_public_id_prefix_and_loose_packets_default(self):
        """tests/test_inventory_snapshot_model.py::InventorySnapshotModelTest::test_public_id_prefix_and_loose_packets_default"""
        snapshot = self._snapshot()
        snapshot.full_clean()
        snapshot.save()
        assert snapshot.public_id.startswith("INV-")
        assert len(snapshot.public_id) == 16
        # loose_packets is optional to fill and defaults to zero.
        assert snapshot.loose_packets == 0
        assert snapshot.snapshot_date == self.today

    def test_one_row_per_date_and_packaging(self):
        """tests/test_inventory_snapshot_model.py::InventorySnapshotModelTest::test_one_row_per_date_and_packaging"""
        self._snapshot().save()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._snapshot(bags=10).save()

    def test_admin_without_flag_rejected(self):
        """tests/test_inventory_snapshot_model.py::InventorySnapshotModelTest::test_admin_without_flag_rejected"""
        with self.assertRaises(ValidationError):
            self._snapshot(actor=self.plain_admin_user).full_clean()

    def test_non_admin_rejected(self):
        """tests/test_inventory_snapshot_model.py::InventorySnapshotModelTest::test_non_admin_rejected"""
        with self.assertRaises(ValidationError):
            self._snapshot(actor=self.outsider).full_clean()

    def test_superuser_allowed(self):
        """tests/test_inventory_snapshot_model.py::InventorySnapshotModelTest::test_superuser_allowed"""
        snapshot = self._snapshot(actor=self.su)
        snapshot.full_clean()
        snapshot.save()
        assert snapshot.id is not None

    def test_derived_bag_and_weight_totals(self):
        """tests/test_inventory_snapshot_model.py::InventorySnapshotModelTest::test_derived_bag_and_weight_totals"""
        snapshot = self._snapshot(bags=400, loose_packets=100)
        snapshot.full_clean()
        snapshot.save()
        # 400 bags x 40 packets = 16000 sealed packets, plus 100 loose.
        assert snapshot.bag_packets == 16000
        assert snapshot.total_packets == 16100
        assert snapshot.total_weight == Decimal("16100.000")

    def test_loose_only_line(self):
        """tests/test_inventory_snapshot_model.py::InventorySnapshotModelTest::test_loose_only_line"""
        # A packaging may legitimately hold nothing but loose stock.
        snapshot = self._snapshot(bags=0, loose_packets=25)
        snapshot.full_clean()
        snapshot.save()
        assert snapshot.bag_packets == 0
        assert snapshot.total_packets == 25
