"""InventoryOperations tests: the daily count, its history, and the two pools.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest import mock

from django.core.exceptions import PermissionDenied, ValidationError

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import add_client_address, create_client
from aggregator.DispatchOperations import sync_dispatch_entry
from aggregator.models import (
    Address,
    City,
    Country,
    InventorySnapshot,
    InwardRawMaterial,
    Party,
    Pincode,
    ProductPackaging,
    Stage,
    StageIds,
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
from common.models import indian_now
from tests.common import DMLTestCase, book_raw_material, book_raw_material_for_every_product


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
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("150.00"), actor=cls.su,
        )
        cls.pack = add_packaging(
            cls.product, packet_weight=Decimal("1.000"), packets=40, actor=cls.su
        )
        # _count_everything counts every packaging, including the dml.sql
        # seed rows, and every count is now checked against raw material.
        book_raw_material_for_every_product(actor=cls.su)
        cls.today = datetime.date.today()
        cls.weight = Decimal("1.000")

    # -- helpers ---------------------------------------------------------------

    def _count_everything(self, *, bags=400, loose_packets=100, snapshot_date=None):
        """Record a complete day's bag count, plus a loose count per pool.

        Bags and loose stock are separate writes on separate tables: bags per
        packaging, loose per (product, packet_weight).
        """
        snapshots = inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), bags),
            actor=self.stock_admin,
            snapshot_date=snapshot_date,
        )
        pools = {
            (pack.product, pack.packet_weight)
            for pack in ProductPackaging.objects.select_related("product")
        }
        inv.record_loose_stocks(
            counts=dict.fromkeys(pools, loose_packets),
            actor=self.stock_admin,
            snapshot_date=snapshot_date,
        )
        return snapshots

    def _order(self, quantity=2, packaging=None):
        return create_order(
            client=self.client_obj,
            delivery_address=self.addr,
            actor=self.sp_user,
            items=[{"product_packaging": packaging or self.pack, "quantity": quantity}],
        )

    def _dispatch(self, order, *, dispatch_date, lr_number, packaging=None, quantities=None):
        """Attach dispatch details and write the challan (status is not moved).

        Mirrors what ``OrderOperations.dispatch_order`` does before flipping the
        order to DISPATCHED. ``consumed_bags``/``reserved_bags`` now read the
        challan's ``DispatchEntryItem.quantity``, not just the order line, so a
        dispatched order needs one of these to mean anything -- a bare status
        flip (as these tests used to do) leaves no record of what shipped.
        """
        packaging = packaging or self.pack
        # A same-day dispatch needs a real, precise timestamp -- InventoryOperations
        # compares it against a count's ``counted_at`` to decide which side of that
        # count it falls on (see ``_dispatch_conditions``). A backdated dispatch
        # (a different calendar day) only needs *a* time on that day.
        dispatched_at = (
            indian_now()
            if dispatch_date == self.today
            else datetime.datetime.combine(
                dispatch_date, datetime.time(), tzinfo=indian_now().tzinfo
            )
        )
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin, dispatch_date=dispatch_date,
            from_city=self.city, to_city=self.city2, lr_number=lr_number,
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
        )
        sync_dispatch_entry(
            order, actor=self.stock_admin,
            dispatched_at=dispatched_at,
            from_city=self.city, to_city=self.city2,
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
            lot_numbers={packaging.public_id: "LOT-1"},
            quantities=quantities,
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
            product_packaging=self.pack, bags=360, actor=self.stock_admin
        )
        rows = InventorySnapshot.objects.filter(
            snapshot_date=self.today, product_packaging=self.pack
        )
        assert rows.count() == 1
        # Opening bags is recorded by re-uploading the count.
        assert rows.first().bags == 360

    def test_older_days_are_kept_but_reads_use_only_the_latest(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_older_days_are_kept_but_reads_use_only_the_latest"""
        yesterday = self.today - datetime.timedelta(days=1)
        self._count_everything(bags=100, snapshot_date=yesterday)
        self._count_everything(bags=400, snapshot_date=self.today)

        # History is kept...
        assert InventorySnapshot.objects.filter(snapshot_date=yesterday).exists()
        # ...but every read sees today's count alone.
        assert inv.latest_snapshot_date() == self.today
        assert inv.on_hand_bags(self.pack) == 400
        assert inv.available_bags(self.pack) == 400
        assert {e["packets_on_hand"] for e in inv.stock_position()} == {400}
        assert inv.snapshot_for().count() == ProductPackaging.objects.count()

    def test_yesterdays_count_does_not_complete_today(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_yesterdays_count_does_not_complete_today"""
        yesterday = self.today - datetime.timedelta(days=1)
        self._count_everything(snapshot_date=yesterday)
        assert inv.is_stock_count_complete() is False

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
        assert inv.available_loose_packets(self.product, self.weight) == 100

        verify_order(self._order(quantity=2), self.stock_admin)

        assert inv.reserved_bags(self.pack) == 2
        assert inv.available_bags(self.pack) == 398
        # The loose pool is untouched by a packaged order.
        assert inv.available_loose_packets(self.product, self.weight) == 100

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
        self._dispatch(order, dispatch_date=self.today, lr_number="LR777")
        update_order_status(order, StatusIds.DISPATCHED)

        assert inv.reserved_bags(self.pack) == 0
        assert inv.consumed_bags(self.pack) == 5
        assert inv.available_bags(self.pack) == 395

        revert_dispatch(order)
        assert inv.reserved_bags(self.pack) == 5
        assert inv.consumed_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 395

    def test_partial_dispatch_leaves_shortfall_reserved(self):
        """Shipping fewer bags than ordered leaves the gap reserved, not consumed.

        4 counted, order for 2, only 1 actually dispatched: 1 consumed, 1 still
        reserved (the undelivered remainder), 2 available, and the live on-hand
        (available + reserved) is 3 -- one bag genuinely left the floor.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_partial_dispatch_leaves_shortfall_reserved
        """
        self._count_everything(bags=4)
        order = self._order(quantity=2)
        verify_order(order, self.stock_admin)
        assert inv.reserved_bags(self.pack) == 2
        assert inv.available_bags(self.pack) == 2

        self._dispatch(
            order,
            dispatch_date=self.today,
            lr_number="LR950",
            quantities={self.pack.public_id: 1},
        )
        update_order_status(order, StatusIds.DISPATCHED)

        assert inv.consumed_bags(self.pack) == 1
        assert inv.reserved_bags(self.pack) == 1
        assert inv.available_bags(self.pack) == 2

        position = next(p for p in inv.stock_position() if p["packaging"] == self.pack)
        assert position["packets_reserved"] == 1
        assert position["packets_consumed"] == 1
        assert position["packets_available"] == 2
        assert position["packets_on_hand"] == 3

    def test_dispatch_before_the_count_is_not_subtracted_twice(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_dispatch_before_the_count_is_not_subtracted_twice"""
        self._count_everything(bags=400)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        self._dispatch(
            order,
            dispatch_date=self.today - datetime.timedelta(days=3),
            lr_number="LR778",
        )
        update_order_status(order, StatusIds.DISPATCHED)

        # Those bags left before today's count was taken, so they are already
        # absent from the counted 400 and must not be subtracted again.
        assert inv.consumed_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 400

    def _dispatch_today(self, order):
        self._dispatch(order, dispatch_date=self.today, lr_number="LR779")
        update_order_status(order, StatusIds.DISPATCHED)

    def test_a_same_day_dispatch_before_the_count_is_not_subtracted_twice(self):
        """Dispatched at 10:00, counted at 17:00: the count already lacks those bags.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_a_same_day_dispatch_before_the_count_is_not_subtracted_twice
        """
        self._count_everything(bags=400)
        raw_before = inv.raw_available_kg(self.product)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        self._dispatch_today(order)

        # The re-count finds the 5 dispatched bags gone from the floor.
        inv.record_stock_count(product_packaging=self.pack, bags=395, actor=self.stock_admin)

        assert inv.consumed_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 395
        # Still spent from raw material: 395 on the floor + 5 on the road.
        assert inv.raw_available_kg(self.product) == raw_before

    def test_a_same_day_dispatch_after_the_count_is_consumed(self):
        """Counted first, dispatched later the same day: subtracted once, not ignored.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_a_same_day_dispatch_after_the_count_is_consumed
        """
        self._count_everything(bags=400)
        raw_before = inv.raw_available_kg(self.product)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        self._dispatch_today(order)

        assert inv.consumed_bags(self.pack) == 5
        assert inv.available_bags(self.pack) == 395
        assert inv.raw_available_kg(self.product) == raw_before

    def test_only_a_count_write_moves_the_count_time(self):
        """An admin edit of a count line keeps ``counted_at``; a re-count moves it.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_only_a_count_write_moves_the_count_time
        """
        self._count_everything(bags=400)
        line = inv.snapshot_line(self.pack)
        counted_at = line.counted_at

        line.full_clean()
        line.save()  # what the Django admin's change form does
        line.refresh_from_db()
        assert line.counted_at == counted_at

        inv.record_stock_count(product_packaging=self.pack, bags=399, actor=self.stock_admin)
        line.refresh_from_db()
        assert line.counted_at > counted_at

    # -- raw material backing ---------------------------------------------------
    #
    # self.product is booked with a huge (1,000,000 kg) raw lot in
    # setUpTestData so every test above can write counts freely. These tests
    # care about the raw-material check itself, so they use a fresh product
    # with a small, exact raw booking instead.

    def _raw_pack(self, *, name, packet_weight=Decimal("1.000"), packets=1):
        """A fresh product + single packaging, 1 bag == ``packet_weight`` kg."""
        product = create_product(
            name=name, crop="Jowar", stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("10.00"), actor=self.su,
        )
        pack = add_packaging(
            product, packet_weight=packet_weight, packets=packets, actor=self.su
        )
        return product, pack

    def test_bag_count_within_raw_material_is_allowed(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_bag_count_within_raw_material_is_allowed"""
        product, pack = self._raw_pack(name="Raw OK")
        book_raw_material(product, Decimal("10.000"), actor=self.su)

        inv.record_stock_count(product_packaging=pack, bags=10, actor=self.stock_admin)
        assert inv.on_hand_bags(pack) == 10
        assert inv.raw_available_kg(product) == Decimal("0.000")

    def test_bag_count_exceeding_raw_material_is_rejected_and_rolled_back(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_bag_count_exceeding_raw_material_is_rejected_and_rolled_back"""
        product, pack = self._raw_pack(name="Raw Short")
        book_raw_material(product, Decimal("10.000"), actor=self.su)

        with self.assertRaises(ValueError):
            inv.record_stock_count(product_packaging=pack, bags=11, actor=self.stock_admin)
        # The rejected write left no row behind.
        assert inv.on_hand_bags(pack) == 0
        assert inv.raw_available_kg(product) == Decimal("10.000")

    def test_lab_testing_lot_provides_no_raw_material(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_lab_testing_lot_provides_no_raw_material"""
        product, pack = self._raw_pack(name="Raw Lab Testing")
        party, _ = Party.objects.get_or_create(
            name="Raw Ops Test Party", city=self.city, defaults={"created_by": self.su}
        )
        InwardRawMaterial.objects.create(
            product=product, party=party, quantity_kg=Decimal("10.000"),
            created_by=self.su,
        )  # default status=lab_testing, effective_date=None

        assert inv.raw_available_kg(product) == Decimal("0.000")
        with self.assertRaises(ValueError):
            inv.record_stock_count(product_packaging=pack, bags=1, actor=self.stock_admin)

    def test_future_effective_date_provides_no_raw_material(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_future_effective_date_provides_no_raw_material"""
        product, pack = self._raw_pack(name="Raw Future")
        book_raw_material(
            product, Decimal("10.000"), actor=self.su,
            effective_date=self.today + datetime.timedelta(days=1),
        )

        assert inv.raw_available_kg(product) == Decimal("0.000")
        with self.assertRaises(ValueError):
            inv.record_stock_count(product_packaging=pack, bags=1, actor=self.stock_admin)

    def test_lowering_a_bag_count_releases_raw_material(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_lowering_a_bag_count_releases_raw_material"""
        product, pack = self._raw_pack(name="Raw Release")
        book_raw_material(product, Decimal("10.000"), actor=self.su)

        inv.record_stock_count(product_packaging=pack, bags=10, actor=self.stock_admin)
        assert inv.raw_available_kg(product) == Decimal("0.000")

        inv.record_stock_count(product_packaging=pack, bags=4, actor=self.stock_admin)
        assert inv.raw_available_kg(product) == Decimal("6.000")

    def test_mixed_increase_and_decrease_is_judged_net_per_product(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_mixed_increase_and_decrease_is_judged_net_per_product"""
        product, pack_a = self._raw_pack(name="Raw Mixed", packets=1)
        pack_b = add_packaging(
            product, packet_weight=Decimal("1.000"), packets=2, actor=self.su
        )
        book_raw_material(product, Decimal("10.000"), actor=self.su)
        inv.record_stock_count(product_packaging=pack_a, bags=8, actor=self.stock_admin)
        assert inv.raw_available_kg(product) == Decimal("2.000")

        # Raising pack_a to 10kg while adding pack_b at 1 (2kg) would be 12kg,
        # over the 10kg available -- rejected and rolled back in full.
        with self.assertRaises(ValueError):
            inv.record_stock_counts(
                counts={pack_a: 10, pack_b: 1}, actor=self.stock_admin,
            )
        assert inv.on_hand_bags(pack_a) == 8
        assert inv.on_hand_bags(pack_b) == 0

        # Lowering pack_a to 6 (6kg) while raising pack_b to 2 (4kg) nets to
        # exactly 10kg -- the whole upload is judged together, not line by line.
        inv.record_stock_counts(counts={pack_a: 6, pack_b: 2}, actor=self.stock_admin)
        assert inv.on_hand_bags(pack_a) == 6
        assert inv.on_hand_bags(pack_b) == 2
        assert inv.raw_available_kg(product) == Decimal("0.000")

    def test_bags_dispatched_before_the_count_stay_spent(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_bags_dispatched_before_the_count_stay_spent"""
        self._count_everything(bags=400)
        before = inv.raw_available_kg(self.product)

        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        self._dispatch(
            order,
            dispatch_date=self.today - datetime.timedelta(days=3),
            lr_number="LR900",
        )
        update_order_status(order, StatusIds.DISPATCHED)

        # The 5 bags left before today's count, so on_hand/consumed already
        # forgot them -- but they were still packed from raw material, and
        # raw availability must not quietly get it back.
        assert inv.consumed_bags(self.pack) == 0
        assert inv.on_hand_bags(self.pack) == 400
        assert inv.raw_available_kg(self.product) == before - 5 * self.pack.total_weight

    def test_reserved_bags_do_not_change_raw_material(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_reserved_bags_do_not_change_raw_material"""
        self._count_everything(bags=400)
        before = inv.raw_available_kg(self.product)

        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)  # reserves 5 bags; none dispatched

        assert inv.reserved_bags(self.pack) == 5
        assert inv.raw_available_kg(self.product) == before

    def test_raw_material_carries_forward_across_a_new_inward_lot(self):
        """A new day's count is a fresh total, not a delta from raw material.

        100kg in stock; 10 bags of 10kg are made (100kg spent) -- 5 dispatch
        the same day, 5 stay. That leaves 0kg available: dispatching same-day
        does not double-spend, since the day's count (10) already included the
        bags that would ship later that day.

        A second 100kg lot arrives tomorrow. Tomorrow's count is 10 again (the
        5 that stayed, plus 5 freshly made) -- the raw check must recognise
        only 5 bags are genuinely new against the new lot, landing on 50kg
        still available out of 200kg ever supplied (150kg ever bagged), not
        rejecting the count or double-charging the carried-forward 5.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_raw_material_carries_forward_across_a_new_inward_lot
        """
        tomorrow = self.today + datetime.timedelta(days=1)

        product2, pack2 = self._raw_pack(
            name="Bajra", packet_weight=Decimal("10.000"), packets=1
        )
        book_raw_material(
            product2, Decimal("100.000"), actor=self.stock_admin, effective_date=self.today
        )

        # Every other packaging just needs *a* count so verification isn't
        # blocked -- pack2 is the one under test.
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.exclude(pk=pack2.pk), 1),
            actor=self.stock_admin,
        )
        # Today's opening count: 10 bags made from the 100kg lot. 5 will ship
        # today; entering 10 (not 5) is what makes the formula work -- see
        # ``on_hand_bags`` on the count being the stale, as-counted figure.
        inv.record_stock_count(product_packaging=pack2, bags=10, actor=self.stock_admin)

        order = self._order(quantity=5, packaging=pack2)
        verify_order(order, self.stock_admin)
        self._dispatch(order, dispatch_date=self.today, lr_number="LR-BAJRA", packaging=pack2)
        update_order_status(order, StatusIds.DISPATCHED)

        assert inv.raw_bagged_kg(product2) == Decimal("100.000")
        assert inv.raw_available_kg(product2) == Decimal("0.000")

        with mock.patch("aggregator.InventoryOperations.today", return_value=tomorrow):
            book_raw_material(
                product2, Decimal("100.000"), actor=self.stock_admin, effective_date=tomorrow
            )
            # Tomorrow's count: the 5 that stayed, plus 5 freshly made.
            inv.record_stock_count(product_packaging=pack2, bags=10, actor=self.stock_admin)

            assert inv.raw_inward_kg(product2) == Decimal("200.000")
            # 15 bags have ever been made (10 yesterday + 5 today) -- 150kg,
            # not 200kg, even though the count only ever shows 10 at a time.
            assert inv.raw_bagged_kg(product2) == Decimal("150.000")
            assert inv.raw_available_kg(product2) == Decimal("50.000")

    def test_higher_next_day_count_allowed_up_to_leftover_raw_material(self):
        """Growing tomorrow's count is fine as long as raw material still covers it --
        no second inward lot needed if yesterday's lot was not fully used.

        400kg in stock; 20 bags of 10kg are made (200kg spent), 10 dispatch,
        10 stay -- 200kg of the original lot is still untouched. Tomorrow's
        count of 30 (the 10 that stayed, plus 20 freshly made) needs exactly
        that leftover 200kg and must be accepted, landing on 0kg available.
        One bag more (31) needs 210kg, which isn't there, and must be refused.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_higher_next_day_count_allowed_up_to_leftover_raw_material
        """
        tomorrow = self.today + datetime.timedelta(days=1)

        product3, pack3 = self._raw_pack(
            name="Ragi", packet_weight=Decimal("10.000"), packets=1
        )
        book_raw_material(
            product3, Decimal("400.000"), actor=self.stock_admin, effective_date=self.today
        )

        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.exclude(pk=pack3.pk), 1),
            actor=self.stock_admin,
        )
        # Today's opening count: 20 bags (200kg) -- 10 will ship today.
        inv.record_stock_count(product_packaging=pack3, bags=20, actor=self.stock_admin)

        order = self._order(quantity=10, packaging=pack3)
        verify_order(order, self.stock_admin)
        self._dispatch(order, dispatch_date=self.today, lr_number="LR-RAGI", packaging=pack3)
        update_order_status(order, StatusIds.DISPATCHED)

        # 200kg spent, 200kg of the 400kg lot still untouched.
        assert inv.raw_bagged_kg(product3) == Decimal("200.000")
        assert inv.raw_available_kg(product3) == Decimal("200.000")

        with mock.patch("aggregator.InventoryOperations.today", return_value=tomorrow):
            # No new inward lot -- same 400kg, no more, no less.
            assert inv.raw_inward_kg(product3) == Decimal("400.000")

            # 31 needs 210kg against the leftover 200kg: refused.
            with self.assertRaises(ValueError):
                inv.record_stock_count(
                    product_packaging=pack3, bags=31, actor=self.stock_admin
                )

            # 30 (10 carried + 20 new) needs exactly the leftover 200kg: allowed.
            inv.record_stock_count(product_packaging=pack3, bags=30, actor=self.stock_admin)
            assert inv.on_hand_bags(pack3) == 30
            assert inv.raw_bagged_kg(product3) == Decimal("400.000")
            assert inv.raw_available_kg(product3) == Decimal("0.000")

    def test_uncounted_packaging_has_no_stock(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_uncounted_packaging_has_no_stock"""
        assert inv.on_hand_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 0
        assert inv.available_loose_packets(self.product, self.weight) == 0

    def test_stock_position_and_payload_shapes(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_stock_position_and_payload_shapes"""
        self._count_everything(bags=400, loose_packets=100)
        position = inv.stock_position()
        # dml.sql seeds packagings of its own, so the count covers those too.
        assert len(position) == ProductPackaging.objects.count()
        mine = next(p for p in position if p["packaging"] == self.pack)
        assert mine["packets_on_hand"] == 400
        # Bags only -- the loose pool is a separate grain and a separate payload.
        assert "product_loose_packets_available" not in mine

        payload = inv.snapshot_payload(inv.snapshot_line(self.pack))
        assert "id" not in payload
        assert payload["public_id"].startswith("INV-")
        assert payload["packaging"]["public_id"] == self.pack.public_id
        assert "loose_packets" not in payload
        assert payload["total_packets"] == 16000

    def test_stock_position_on_hand_excludes_todays_dispatches(self):
        """``packets_on_hand`` is the live present total (available + reserved),
        not the raw count -- a bag dispatched today no longer counts as on
        hand even though today's count still includes it.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_stock_position_on_hand_excludes_todays_dispatches
        """
        self._count_everything(bags=400)

        reserved_order = self._order(quantity=5)
        verify_order(reserved_order, self.stock_admin)  # reserves 5, stays CONFIRMED

        dispatched_order = self._order(quantity=3)
        verify_order(dispatched_order, self.stock_admin)
        self._dispatch(dispatched_order, dispatch_date=self.today, lr_number="LR901")
        update_order_status(dispatched_order, StatusIds.DISPATCHED)

        # The raw count itself never changes -- it's the day's opening balance.
        assert inv.on_hand_bags(self.pack) == 400
        assert inv.reserved_bags(self.pack) == 5
        assert inv.consumed_bags(self.pack) == 3
        assert inv.available_bags(self.pack) == 392  # 400 - 5 - 3

        position = next(p for p in inv.stock_position() if p["packaging"] == self.pack)
        assert position["packets_reserved"] == 5
        assert position["packets_consumed"] == 3
        assert position["packets_available"] == 392
        # Live on hand = available + reserved = 397, NOT the raw count of 400:
        # the 3 dispatched bags are gone even though today's count still has them.
        assert position["packets_on_hand"] == 397
