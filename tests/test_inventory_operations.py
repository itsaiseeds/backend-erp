"""InventoryOperations tests: the daily count, its purge, and the two pools.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import add_client_address, create_client
from aggregator.models import (
    Address,
    City,
    Country,
    InventorySnapshot,
    Pincode,
    ProductPackaging,
    State,
    StatusIds,
)
from aggregator.OrderOperations import (
    attach_dispatch_details,
    create_order,
    revert_dispatch,
    unverify_order,
    update_order_status,
    verify_order,
)
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import Admin, SalesPerson, User
from tests.common import DMLTestCase


class InventoryOperationsTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.sp_user = User.objects.create_user(
            "9200000001", "Sales Person", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.stock_admin = User.objects.create_user(
            "9200000002", "Stock Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.plain_admin = User.objects.create_user(
            "9200000003", "Plain Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        Admin.objects.create(
            user=cls.stock_admin, created_by=cls.su, can_update_stock_count=True
        )
        Admin.objects.create(
            user=cls.plain_admin, created_by=cls.su, can_update_stock_count=False
        )

        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.su}
        )
        cls.state = State.objects.create(name="Maharashtra", country=cls.country, created_by=cls.su)
        cls.city = City.objects.create(name="Pune", state=cls.state, created_by=cls.su)
        cls.city2 = City.objects.create(name="Nashik", state=cls.state, created_by=cls.su)
        cls.pincode = Pincode.objects.create(code="411002", city=cls.city, created_by=cls.su)
        SalesPerson.objects.create(user=cls.sp_user, city=cls.city, created_by=cls.su)

        cls.addr = Address.objects.create(
            address_line_1="2 Market Rd", pincode=cls.pincode, city=cls.city,
            state=cls.state, country=cls.country, created_by=cls.su,
        )
        cls.client_obj = create_client(
            company_name="Bharat Agro", gst_number="27AAPFU0939F1ZV", actor=cls.sp_user
        )
        add_client_address(cls.client_obj, cls.addr, cls.sp_user, is_primary=True)

        cls.product = create_product(
            name="Hybrid Jowar", crop="Jowar",
            buying_price=Decimal("100.00"), selling_price=Decimal("150.00"), actor=cls.su,
        )
        cls.pack = add_packaging(
            cls.product, packet_weight=Decimal("1.000"), packets=40, actor=cls.su
        )
        cls.today = datetime.date.today()

    # -- helpers ---------------------------------------------------------------

    def _count_everything(self, *, bags=400, loose_packets=100, snapshot_date=None):
        """Record a complete day's count covering every active packaging."""
        return inv.record_stock_counts(
            counts={
                pack: {"bags": bags, "loose_packets": loose_packets}
                for pack in ProductPackaging.objects.all()
            },
            actor=self.stock_admin,
            snapshot_date=snapshot_date,
        )

    def _order(self, quantity=2):
        return create_order(
            client=self.client_obj,
            delivery_address=self.addr,
            actor=self.sp_user,
            items=[{"product_packaging": self.pack, "quantity": quantity}],
        )

    # -- writing the count -----------------------------------------------------

    def test_admin_without_flag_cannot_record(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_admin_without_flag_cannot_record"""
        with self.assertRaises(PermissionDenied):
            inv.record_stock_count(
                product_packaging=self.pack, bags=10, actor=self.plain_admin
            )

    def test_salesperson_cannot_record(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_salesperson_cannot_record"""
        with self.assertRaises(PermissionDenied):
            inv.record_stock_count(
                product_packaging=self.pack, bags=10, actor=self.sp_user
            )

    def test_recount_overwrites_rather_than_duplicating(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_recount_overwrites_rather_than_duplicating"""
        inv.record_stock_count(
            product_packaging=self.pack, bags=400, actor=self.stock_admin
        )
        inv.record_stock_count(
            product_packaging=self.pack, bags=360, loose_packets=40, actor=self.stock_admin
        )
        rows = InventorySnapshot.objects.filter(
            snapshot_date=self.today, product_packaging=self.pack
        )
        assert rows.count() == 1
        # Opening bags to make loose stock is recorded by re-uploading.
        assert rows.first().bags == 360
        assert rows.first().loose_packets == 40

    def test_newer_count_hard_deletes_older_days_only(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_newer_count_hard_deletes_older_days_only"""
        yesterday = self.today - datetime.timedelta(days=1)
        self._count_everything(bags=100, snapshot_date=yesterday)
        assert InventorySnapshot.objects.filter(snapshot_date=yesterday).exists()

        self._count_everything(bags=400, snapshot_date=self.today)

        # Rows for days < x are physically gone, not merely soft-deleted.
        assert not InventorySnapshot.all_objects.filter(snapshot_date=yesterday).exists()
        # Rows for x itself survive.
        assert InventorySnapshot.objects.filter(snapshot_date=self.today).exists()
        assert inv.latest_snapshot_date() == self.today

    # -- completeness gate -----------------------------------------------------

    def test_count_is_incomplete_until_every_packaging_is_covered(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_count_is_incomplete_until_every_packaging_is_covered"""
        self._count_everything()
        assert inv.is_stock_count_complete() is True

        # A packaging added after the count reopens the gap: the count is only
        # complete when it covers every active packaging.
        other = add_packaging(
            self.product, packet_weight=Decimal("1.500"), packets=20, actor=self.su
        )
        assert inv.is_stock_count_complete() is False
        assert other in list(inv.missing_packagings())

        inv.record_stock_count(
            product_packaging=other, bags=50, actor=self.stock_admin
        )
        assert inv.is_stock_count_complete() is True
        assert not inv.missing_packagings().exists()

    def test_verification_blocked_until_the_count_is_uploaded(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_verification_blocked_until_the_count_is_uploaded"""
        order = self._order()
        with self.assertRaises(ValidationError):
            verify_order(order, self.stock_admin)

        self._count_everything()
        verify_order(order, self.stock_admin)
        assert order.status.code == "CONFIRMED"

    # -- the two pools ---------------------------------------------------------

    def test_packaged_order_never_touches_loose_stock(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_packaged_order_never_touches_loose_stock"""
        self._count_everything(bags=400, loose_packets=100)
        assert inv.available_bags(self.pack) == 400
        assert inv.available_loose_packets(self.product) == 100

        verify_order(self._order(quantity=2), self.stock_admin)

        assert inv.reserved_bags(self.pack) == 2
        assert inv.available_bags(self.pack) == 398
        # The loose pool is untouched by a packaged order.
        assert inv.available_loose_packets(self.product) == 100

    def test_verify_order_blocked_when_insufficient_stock(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_verify_order_blocked_when_insufficient_stock"""
        # Only 3 bags on hand for self.pack; an order for 5 cannot be verified.
        self._count_everything(bags=3)
        big = self._order(quantity=5)
        with self.assertRaises(ValidationError):
            verify_order(big, self.stock_admin)
        big.refresh_from_db()
        assert big.status.code != "CONFIRMED"
        assert inv.reserved_bags(self.pack) == 0

        # An order within the available 3 verifies fine.
        ok = self._order(quantity=2)
        verify_order(ok, self.stock_admin)
        assert ok.status.code == "CONFIRMED"
        assert inv.available_bags(self.pack) == 1

    def test_verify_order_blocked_when_stock_already_reserved(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_verify_order_blocked_when_stock_already_reserved"""
        self._count_everything(bags=4)
        first = self._order(quantity=3)
        verify_order(first, self.stock_admin)  # reserves 3, leaves 1
        second = self._order(quantity=2)
        with self.assertRaises(ValidationError):
            verify_order(second, self.stock_admin)  # needs 2, only 1 left
        assert inv.available_bags(self.pack) == 1

    def test_verification_is_reversible(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_verification_is_reversible"""
        self._count_everything(bags=400)
        order = self._order(quantity=3)
        verify_order(order, self.stock_admin)
        assert inv.available_bags(self.pack) == 397

        unverify_order(order)
        assert order.verified_by_id is None
        assert order.verified_at is None
        assert order.status.code == "UNDER_REVIEW"
        assert inv.available_bags(self.pack) == 400

    def test_dispatch_moves_packets_from_reserved_to_consumed_and_back(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_dispatch_moves_packets_from_reserved_to_consumed_and_back"""
        self._count_everything(bags=400)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin, dispatch_date=self.today,
            from_city=self.city, to_city=self.city2, lr_number="LR777",
        )
        update_order_status(order, StatusIds.DISPATCHED)

        assert inv.reserved_bags(self.pack) == 0
        assert inv.consumed_bags(self.pack) == 5
        assert inv.available_bags(self.pack) == 395

        revert_dispatch(order)
        assert inv.reserved_bags(self.pack) == 5
        assert inv.consumed_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 395

    def test_dispatch_before_the_count_is_not_subtracted_twice(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_dispatch_before_the_count_is_not_subtracted_twice"""
        self._count_everything(bags=400)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin,
            dispatch_date=self.today - datetime.timedelta(days=3),
            from_city=self.city, to_city=self.city2, lr_number="LR778",
        )
        update_order_status(order, StatusIds.DISPATCHED)

        # Those bags left before today's count was taken, so they are already
        # absent from the counted 400 and must not be subtracted again.
        assert inv.consumed_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 400

    def test_uncounted_packaging_has_no_stock(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_uncounted_packaging_has_no_stock"""
        assert inv.on_hand_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 0
        assert inv.available_loose_packets(self.product) == 0

    def test_stock_position_and_payload_shapes(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_stock_position_and_payload_shapes"""
        self._count_everything(bags=400, loose_packets=100)
        position = inv.stock_position()
        # dml.sql seeds packagings of its own, so the count covers those too.
        assert len(position) == ProductPackaging.objects.count()
        mine = next(p for p in position if p["packaging"] == self.pack)
        assert mine["packets_on_hand"] == 400
        assert mine["product_loose_packets_available"] == 100

        payload = inv.snapshot_payload(inv.snapshot_line(self.pack))
        assert "id" not in payload
        assert payload["public_id"].startswith("INV-")
        assert payload["packaging"]["public_id"] == self.pack.public_id
        assert payload["product_loose_packets_available"] == 100
        assert payload["total_packets"] == 16100
