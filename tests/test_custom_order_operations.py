"""CustomOrder + loose-pool tests.

A custom order has no verification step -- it is auto-verified (CONFIRMED) on
creation, and creation is blocked unless enough loose packets are in stock.
Covers the loose-packet reserve/consume math and a strict dispatch-reversal
scenario.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import add_client_address, create_client
from aggregator.CustomOrderOperations import (
    add_custom_order_item,
    attach_dispatch_details,
    create_custom_order,
    revert_dispatch,
    update_custom_order_status,
)
from aggregator.models import (
    Address,
    City,
    Country,
    CustomOrder,
    Pincode,
    ProductPackaging,
    State,
    StatusIds,
)
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import Admin, SalesPerson, User
from tests.common import DMLTestCase


class CustomOrderOperationsTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.sp_user = User.objects.create_user(
            "9300000001", "Sales Person", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.stock_admin = User.objects.create_user(
            "9300000002", "Stock Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.plain_user = User.objects.create_user(
            "9300000003", "Plain User", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        Admin.objects.create(
            user=cls.stock_admin, created_by=cls.su, can_update_stock_count=True
        )

        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.su}
        )
        cls.state = State.objects.create(name="Maharashtra", country=cls.country, created_by=cls.su)
        cls.city = City.objects.create(name="Pune", state=cls.state, created_by=cls.su)
        cls.city2 = City.objects.create(name="Nashik", state=cls.state, created_by=cls.su)
        cls.pincode = Pincode.objects.create(code="411003", city=cls.city, created_by=cls.su)
        SalesPerson.objects.create(user=cls.sp_user, city=cls.city, created_by=cls.su)

        cls.addr = Address.objects.create(
            address_line_1="3 Loose Rd", pincode=cls.pincode, city=cls.city,
            state=cls.state, country=cls.country, created_by=cls.su,
        )
        cls.addr_other = Address.objects.create(
            address_line_1="4 Nowhere", pincode=cls.pincode, city=cls.city,
            state=cls.state, country=cls.country, created_by=cls.su,
        )
        cls.client_obj = create_client(
            company_name="Loose Traders", gst_number="27AAPFU0939F1ZV", actor=cls.sp_user
        )
        add_client_address(cls.client_obj, cls.addr, cls.sp_user, is_primary=True)

        cls.product = create_product(
            name="Hybrid Cotton", crop="Cotton",
            buying_price=Decimal("100.00"), selling_price=Decimal("150.00"), actor=cls.su,
        )
        # Two packagings of the SAME product, so on-hand loose sums across both.
        cls.pack_a = add_packaging(
            cls.product, packet_weight=Decimal("1.000"), packets=40,
            actor=cls.su,
        )
        cls.pack_b = add_packaging(
            cls.product, packet_weight=Decimal("1.500"), packets=20,
            actor=cls.su,
        )
        cls.other_product = create_product(
            name="Hybrid Wheat", crop="Wheat",
            buying_price=Decimal("80.00"), selling_price=Decimal("120.00"), actor=cls.su,
        )
        cls.other_pack = add_packaging(
            cls.other_product, packet_weight=Decimal("1.000"), packets=50,
            actor=cls.su,
        )
        cls.today = datetime.date.today()

    # -- helpers ---------------------------------------------------------------

    def _count(self, *, loose_packets=100, bags=400, snapshot_date=None):
        """Upload a complete day's count: every packaging gets bags + loose packets."""
        return inv.record_stock_counts(
            counts={
                pack: {"bags": bags, "loose_packets": loose_packets}
                for pack in ProductPackaging.objects.all()
            },
            actor=self.stock_admin,
            snapshot_date=snapshot_date,
        )

    def _custom_order(self, *, packets=30, product=None, actor=None):
        return create_custom_order(
            client=self.client_obj,
            delivery_address=self.addr,
            actor=actor or self.stock_admin,
            items=[{"product": product or self.product, "packets": packets}],
        )

    def _dispatch(self, order, *, date=None):
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin, dispatch_date=date or self.today,
            from_city=self.city, to_city=self.city2, lr_number="LR-CO",
        )
        update_custom_order_status(order, StatusIds.DISPATCHED)

    # -- creation rules --------------------------------------------------------

    def test_only_admins_can_create_custom_orders(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_only_admins_can_create_custom_orders"""
        self._count()  # stock present, so the block can only come from the role
        with self.assertRaises(ValidationError):
            self._custom_order(actor=self.sp_user)
        with self.assertRaises(ValidationError):
            self._custom_order(actor=self.plain_user)
        order = self._custom_order(actor=self.stock_admin)
        assert order.public_id.startswith("CORD-")

    def test_creation_auto_verifies_the_order(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_creation_auto_verifies_the_order"""
        self._count(loose_packets=100)
        order = self._custom_order(packets=30)
        # Born verified -- no separate verify step.
        assert order.status.code == "CONFIRMED"
        assert order.is_verified
        assert order.verified_by_id == self.stock_admin.id
        assert order.verified_at is not None
        # And it reserves immediately.
        assert inv.reserved_loose_packets(self.product) == 30

    def test_no_packaging_and_totals_in_packets(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_no_packaging_and_totals_in_packets"""
        self._count()
        order = self._custom_order(packets=30)
        item = order.items.get()
        assert item.product_id == self.product.id
        assert not hasattr(item, "product_packaging_id")
        assert item.negotiated_selling_price == Decimal("150.00")  # product per-packet price
        assert item.line_total == Decimal("4500.00")  # 150 * 30
        assert order.total_packets == 30

    def test_delivery_address_must_belong_to_client(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_delivery_address_must_belong_to_client"""
        self._count()
        with self.assertRaises(ValidationError):
            create_custom_order(
                client=self.client_obj, delivery_address=self.addr_other, actor=self.stock_admin,
                items=[{"product": self.product, "packets": 5}],
            )

    def test_one_line_per_product(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_one_line_per_product"""
        self._count()
        order = self._custom_order(packets=10)
        with self.assertRaises(ValidationError):
            add_custom_order_item(
                order, product=self.product, packets=5, actor=self.stock_admin
            )

    # -- the stock gate --------------------------------------------------------

    def test_cannot_create_without_any_stock(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_cannot_create_without_any_stock"""
        # No count uploaded at all -> zero loose packets available.
        with self.assertRaises(ValidationError):
            self._custom_order(packets=1)
        assert CustomOrder.objects.count() == 0

    def test_cannot_create_when_stock_insufficient(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_cannot_create_when_stock_insufficient"""
        self._count(loose_packets=10)  # 2 packagings -> 20 available for the product
        with self.assertRaises(ValidationError):
            self._custom_order(packets=25)
        # Nothing created, nothing reserved.
        assert CustomOrder.objects.count() == 0
        assert inv.reserved_loose_packets(self.product) == 0
        assert inv.available_loose_packets(self.product) == 20

    def test_stock_gate_accounts_for_earlier_orders(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_stock_gate_accounts_for_earlier_orders"""
        self._count(loose_packets=10)  # 20 available
        self._custom_order(packets=15)  # ok, reserves 15 -> 5 left
        assert inv.available_loose_packets(self.product) == 5
        # A second order needing 10 can't be created against the remaining 5.
        with self.assertRaises(ValidationError):
            self._custom_order(packets=10)
        assert CustomOrder.objects.count() == 1

    # -- pool math -------------------------------------------------------------

    def test_loose_on_hand_sums_across_a_products_packagings(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_loose_on_hand_sums_across_a_products_packagings"""
        self._count(loose_packets=100)  # two packagings of self.product
        assert inv.on_hand_loose_packets(self.product) == 200
        assert inv.available_loose_packets(self.product) == 200

    def test_loose_reservation_is_isolated_per_product(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_loose_reservation_is_isolated_per_product"""
        self._count(loose_packets=100)
        self._custom_order(packets=30, product=self.product)
        # The other product's loose pool is untouched (it has one packaging: 100).
        assert inv.reserved_loose_packets(self.other_product) == 0
        assert inv.available_loose_packets(self.other_product) == 100

    def test_loose_pool_never_touched_by_bag_math(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_loose_pool_never_touched_by_bag_math"""
        self._count(loose_packets=100, bags=400)
        self._custom_order(packets=30)
        # Creating a custom order moves loose packets only; whole bags unaffected.
        assert inv.available_bags(self.pack_a) == 400
        assert inv.available_bags(self.pack_b) == 400

    # -- STRICT: dispatch reversed --------------------------------------------

    def test_dispatch_reversal_moves_loose_packets_back_to_reserved(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_dispatch_reversal_moves_loose_packets_back_to_reserved"""
        self._count(loose_packets=100)  # 200 on hand
        order = self._custom_order(packets=30)  # auto-CONFIRMED, reserves 30
        assert inv.reserved_loose_packets(self.product) == 30
        assert inv.available_loose_packets(self.product) == 170

        self._dispatch(order)
        assert inv.reserved_loose_packets(self.product) == 0
        assert inv.consumed_loose_packets(self.product) == 30
        assert inv.available_loose_packets(self.product) == 170

        # Reverse the dispatch: packets return to reserved, still 170 available.
        revert_dispatch(order)
        assert order.status.code == "CONFIRMED"
        assert order.actual_delivery_date is None
        assert inv.reserved_loose_packets(self.product) == 30
        assert inv.consumed_loose_packets(self.product) == 0
        assert inv.available_loose_packets(self.product) == 170

    def test_dispatch_before_count_not_subtracted_twice(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_dispatch_before_count_not_subtracted_twice"""
        self._count(loose_packets=100)
        order = self._custom_order(packets=30)
        self._dispatch(order, date=self.today - datetime.timedelta(days=2))
        # Dispatched before the count -> already gone, not subtracted again.
        assert inv.consumed_loose_packets(self.product) == 0
        assert inv.available_loose_packets(self.product) == 200

    # -- both pools together ---------------------------------------------------

    def test_both_pools_move_independently(self):
        """tests/test_custom_order_operations.py::CustomOrderOperationsTest::test_both_pools_move_independently"""
        from aggregator.OrderOperations import create_order, verify_order

        self._count(loose_packets=100, bags=400)

        # A normal packaged order encumbers whole bags on pack_a only.
        normal = create_order(
            client=self.client_obj, delivery_address=self.addr, actor=self.sp_user,
            items=[{"product_packaging": self.pack_a, "quantity": 6}],
        )
        verify_order(normal, self.stock_admin)

        # A custom order encumbers loose packets on the product.
        self._custom_order(packets=25)

        assert inv.reserved_bags(self.pack_a) == 6
        assert inv.consumed_bags(self.pack_a) == 0
        assert inv.reserved_loose_packets(self.product) == 25
        assert inv.consumed_loose_packets(self.product) == 0

        assert inv.available_bags(self.pack_a) == 394
        assert inv.available_bags(self.pack_b) == 400  # untouched
        assert inv.available_loose_packets(self.product) == 175
