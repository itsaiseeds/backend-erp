"""InventoryOperations tests: the daily count, its history, and the two pools.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations
from aggregator.ClientOperations import add_client_address, create_client
from aggregator.models import (
    Address,
    City,
    Country,
    InventorySnapshot,
    InwardOtherMaterial,
    InwardRawMaterial,
    Order,
    OtherMaterialRecipe,
    OtherMaterialType,
    OtherMaterialUnitType,
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
    mark_delivered,
    revert_dispatch,
    unverify_order,
    update_order_status,
    verify_order,
)
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import Admin, SalesPerson, User
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
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin, dispatch_date=self.today,
            from_city=self.city, to_city=self.city2, lr_number="LR777",
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
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
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
        )
        update_order_status(order, StatusIds.DISPATCHED)

        # Those bags left before today's count was taken, so they are already
        # absent from the counted 400 and must not be subtracted again.
        assert inv.consumed_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 400

    def _dispatch_today(self, order):
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin, dispatch_date=self.today,
            from_city=self.city, to_city=self.city2, lr_number="LR779",
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
        )
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
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin,
            dispatch_date=self.today - datetime.timedelta(days=3),
            from_city=self.city, to_city=self.city2, lr_number="LR900",
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
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

    # -- packing (other) material backing -----------------------------------------
    #
    # A recipe charges ``quantity`` units of its material per packet of its
    # product at its packet weight. self.pack is 40 x 1kg packets per bag.

    def _material(self, name="Test leaflets"):
        return OtherMaterialType.objects.create(
            name=name, unit_type=OtherMaterialUnitType.COUNT, created_by=self.su
        )

    def _recipe(self, material, *, product=None, packet_weight=None, per_packet="2"):
        return OtherMaterialRecipe.objects.create(
            product=product or self.product,
            material_type=material,
            packet_weight=packet_weight or self.pack.packet_weight,
            quantity=Decimal(per_packet),
            created_by=self.su,
        )

    def _receive(self, recipe, quantity):
        party, _ = Party.objects.get_or_create(
            name="Packing Supplier", city=self.city, defaults={"created_by": self.su}
        )
        return InwardOtherMaterial.objects.create(
            recipe=recipe,
            party=party,
            quantity=Decimal(quantity),
            effective_date=self.today,
            created_by=self.su,
        )

    def _on_hand(self, material):
        lines = {
            line["material_type_id"]: line["on_hand"]
            for line in InwardOperations.other_material_on_hand()
        }
        return lines[material.id]

    def test_counted_bags_and_loose_packets_use_packing_material(self):
        """3 bags x 40 packets + 10 loose, at 2 leaflets a packet = 260 used.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_counted_bags_and_loose_packets_use_packing_material
        """
        leaflets = self._material()
        self._receive(self._recipe(leaflets), 1000)

        inv.record_stock_count(product_packaging=self.pack, bags=3, actor=self.stock_admin)
        inv.record_loose_stock(
            product=self.product, packet_weight=self.weight, packets=10, actor=self.stock_admin
        )

        assert inv.other_material_used([leaflets.id]) == {leaflets.id: Decimal("260")}
        assert self._on_hand(leaflets) == Decimal("740")

    def test_bags_dispatched_before_the_count_stay_used(self):
        """Gone from the floor, but they were packed -- their leaflets stay spent.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_bags_dispatched_before_the_count_stay_used
        """
        self._count_everything(bags=400, loose_packets=0)
        leaflets = self._material()
        self._receive(self._recipe(leaflets, per_packet="1"), 100000)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin,
            dispatch_date=self.today - datetime.timedelta(days=3),
            from_city=self.city, to_city=self.city2, lr_number="LR901",
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
        )
        update_order_status(order, StatusIds.DISPATCHED)

        # 400 on the floor + 5 dispatched before the count, 40 packets a bag.
        assert inv.other_material_used([leaflets.id]) == {leaflets.id: Decimal(405 * 40)}

    def test_a_recipe_charges_only_its_own_weight_and_products_share_a_material(self):
        """A 2kg recipe ignores 1kg packets; two products' recipes draw one pool.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_a_recipe_charges_only_its_own_weight_and_products_share_a_material
        """
        leaflets = self._material()
        self._receive(self._recipe(leaflets, packet_weight=Decimal("2.000")), 1000)
        other_product, other_pack = self._raw_pack(name="Leaflet Sharer", packets=10)
        book_raw_material(other_product, Decimal("1000"), actor=self.su)
        self._recipe(leaflets, product=other_product, packet_weight=other_pack.packet_weight,
                     per_packet="3")

        inv.record_stock_count(product_packaging=self.pack, bags=3, actor=self.stock_admin)
        inv.record_stock_count(product_packaging=other_pack, bags=2, actor=self.stock_admin)

        # self.pack is 1kg, which the 2kg recipe does not cover: only the
        # other product's 2 bags x 10 packets x 3 leaflets are charged.
        assert self._on_hand(leaflets) == Decimal("940")

    def test_a_count_that_outruns_packing_material_is_rolled_back(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_a_count_that_outruns_packing_material_is_rolled_back"""
        leaflets = self._material()
        self._receive(self._recipe(leaflets), 160)  # exactly 2 bags' worth
        inv.record_stock_count(product_packaging=self.pack, bags=2, actor=self.stock_admin)

        with self.assertRaisesMessage(ValueError, "'Test leaflets' short by 80"):
            inv.record_stock_counts(counts={self.pack: 3}, actor=self.stock_admin)

        assert inv.on_hand_bags(self.pack) == 2
        assert self._on_hand(leaflets) == Decimal("0")

    def test_a_material_already_short_only_blocks_counts_that_use_more(self):
        """Inward lagging behind the counts: lowering is allowed, raising is not.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_a_material_already_short_only_blocks_counts_that_use_more
        """
        inv.record_stock_count(product_packaging=self.pack, bags=5, actor=self.stock_admin)
        leaflets = self._material()
        self._receive(self._recipe(leaflets), 100)  # 5 bags need 400
        assert self._on_hand(leaflets) == Decimal("-300")

        inv.record_stock_count(product_packaging=self.pack, bags=4, actor=self.stock_admin)
        inv.record_stock_count(product_packaging=self.pack, bags=4, actor=self.stock_admin)
        assert self._on_hand(leaflets) == Decimal("-220")

        with self.assertRaisesMessage(ValueError, "Not enough packing material"):
            inv.record_stock_count(product_packaging=self.pack, bags=6, actor=self.stock_admin)
        assert inv.on_hand_bags(self.pack) == 4

    # -- deleting counts and inward lots ------------------------------------------
    #
    # mark_deleted() is the API's path, delete(deleted_by=...) the Django
    # admin's; both run the model's guard_soft_delete.

    def test_a_count_line_under_reservations_cannot_be_deleted(self):
        """Deleting today's line would leave the reserved bags uncovered.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_a_count_line_under_reservations_cannot_be_deleted
        """
        self._count_everything(bags=400)
        verify_order(self._order(quantity=5), self.stock_admin)
        line = inv.snapshot_line(self.pack)

        for delete in (lambda: line.mark_deleted(self.stock_admin),
                       lambda: line.delete(deleted_by=self.su)):
            with self.assertRaisesMessage(ValidationError, "short by 5 bags"):
                delete()
            assert not line.is_deleted  # the in-memory flags are put back too
            line.refresh_from_db()
            assert not line.is_deleted
        assert inv.available_bags(self.pack) == 395

    def test_a_count_line_nothing_depends_on_can_be_deleted(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_a_count_line_nothing_depends_on_can_be_deleted"""
        self._count_everything(bags=400)
        line = inv.snapshot_line(self.pack)

        line.delete(deleted_by=self.su)

        line.refresh_from_db()
        assert line.is_deleted
        assert inv.available_bags(self.pack) == 0

    def test_a_packing_lot_already_used_cannot_be_deleted(self):
        """Deleting the lot would leave 240 leaflets' worth of counted packets uncovered.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_a_packing_lot_already_used_cannot_be_deleted
        """
        leaflets = self._material()
        recipe = self._recipe(leaflets)
        used_lot = self._receive(recipe, 240)
        spare_lot = self._receive(recipe, 50)
        inv.record_stock_count(product_packaging=self.pack, bags=3, actor=self.stock_admin)

        spare_lot.mark_deleted(self.stock_admin)  # 240 still covers 240 used

        with self.assertRaisesMessage(ValidationError, "'Test leaflets' short by 240.000 count"):
            used_lot.mark_deleted(self.stock_admin)
        used_lot.refresh_from_db()
        assert not used_lot.is_deleted
        assert self._on_hand(leaflets) == Decimal("0")

    def test_the_admin_cannot_delete_raw_material_already_packed(self):
        """The API always refused this; the admin delete now does too.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_the_admin_cannot_delete_raw_material_already_packed
        """
        product, pack = self._raw_pack(name="Admin Raw")
        lot = book_raw_material(product, Decimal("10"), actor=self.su)
        inv.record_stock_count(product_packaging=pack, bags=4, actor=self.stock_admin)

        with self.assertRaisesMessage(ValidationError, "4.000 kg of this lot is already packed"):
            lot.delete(deleted_by=self.su)
        lot.refresh_from_db()
        assert not lot.is_deleted

    # -- deleting orders ------------------------------------------------------------

    def test_an_order_holding_stock_cannot_be_deleted(self):
        """Confirmed, dispatched and delivered orders refuse, via the API or the admin.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_an_order_holding_stock_cannot_be_deleted
        """
        self._count_everything(bags=400)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)

        with self.assertRaisesMessage(ValidationError, "Cannot delete an order that is CONFIRMED"):
            order.delete(deleted_by=self.su)
        attach_dispatch_details(
            order, dispatched_by=self.stock_admin, dispatch_date=self.today,
            from_city=self.city, to_city=self.city2, lr_number="LR902",
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
        )
        update_order_status(order, StatusIds.DISPATCHED)
        with self.assertRaisesMessage(ValidationError, "Cannot delete an order that is DISPATCHED"):
            order.mark_deleted(self.stock_admin)
        mark_delivered(order)
        with self.assertRaisesMessage(ValidationError, "Cannot delete an order that is DELIVERED"):
            order.mark_deleted(self.stock_admin)

        order.refresh_from_db()
        assert not order.is_deleted
        assert inv.consumed_bags(self.pack) == 5

    def test_an_unverified_order_can_be_deleted_and_holds_nothing(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_an_unverified_order_can_be_deleted_and_holds_nothing"""
        self._count_everything(bags=400)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        unverify_order(order)

        order.delete(deleted_by=self.su)

        order.refresh_from_db()
        assert order.is_deleted
        assert inv.available_bags(self.pack) == 400

    def test_an_order_already_deleted_holds_no_stock(self):
        """A row deleted before the guard existed no longer reserves or consumes.

        tests/test_inventory_operations.py::InventoryOperationsTest::test_an_order_already_deleted_holds_no_stock
        """
        self._count_everything(bags=400)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)
        assert inv.reserved_bags(self.pack) == 5

        Order.all_objects.filter(pk=order.pk).update(is_deleted=True)

        assert inv.reserved_bags(self.pack) == 0
        assert inv.available_bags(self.pack) == 400

    def test_only_a_dispatched_order_can_be_delivered(self):
        """tests/test_inventory_operations.py::InventoryOperationsTest::test_only_a_dispatched_order_can_be_delivered"""
        self._count_everything(bags=400)
        order = self._order(quantity=5)
        verify_order(order, self.stock_admin)

        with self.assertRaisesMessage(ValidationError, "Cannot deliver an order that is CONFIRMED"):
            mark_delivered(order)

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
        attach_dispatch_details(
            dispatched_order, dispatched_by=self.stock_admin,
            dispatch_date=self.today,
            from_city=self.city, to_city=self.city2, lr_number="LR901",
            driver_name="Suresh Driver", driver_number="9876500010",
            vehicle_number="GJ05AB5678",
        )
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
