"""Stock ledger recording: which writes create events, and exactly what they hold.

Every test drives real operations and then reads the stored ``StockEvent`` /
``StockEventLine`` rows. The ledger is the diff of the live figures around each
write, so what matters here is *which* events appear, with which detail, which
pools they touch -- and, as importantly, which writes leave no row at all.

Run: bash scripts/run.sh test-serial tests/test_stock_ledger_operations.py
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from functools import partial

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations
from aggregator.CustomOrderOperations import delete_custom_order
from aggregator.CustomOrderOperations import revert_dispatch as revert_custom
from aggregator.models import (
    VALID_DETAILS,
    InventorySnapshot,
    Status,
    StockEvent,
    StockPoolKind,
)
from aggregator.OrderOperations import (
    hold_order,
    mark_delivered,
    reject_order,
    revert_dispatch,
    sync_order_items,
    unverify_order,
    verify_order,
)
from aggregator.ProductOperations import add_packaging
from tests.stock_ledger_support import W1, LedgerWorldTestCase


def line_for(event, kind, **match):
    """The one line of ``event`` for a pool of ``kind`` (optionally narrowed)."""
    found = [
        line
        for line in event.lines.all()
        if line.pool_kind == kind
        and all(getattr(line, key) == value for key, value in match.items())
    ]
    assert len(found) == 1, (kind, match, found)
    return found[0]


class StockLedgerOperationsTest(LedgerWorldTestCase):
    def setUp(self):
        super().setUp()
        self.raw(self.product, "100000")
        self.raw(self.other_product, "100000")
        self.pouches("100000")
        # A complete count: orders can only be verified against a full one.
        self.count_everything({self.pp1: 50, self.qq1: 50})
        self.mark = self.marker()

    # -- orders --------------------------------------------------------------------

    def test_verify_and_every_release_of_an_order(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_verify_and_every_release_of_an_order"""
        order = self.order(self.pp1, 4, verify=False)
        self.assertEqual(self.kinds_since(self.mark), [], "booking an order moves no stock")

        verify_order(order, self.su)
        [event] = self.events_since(self.mark)
        self.assertEqual(
            self.kinds_since(self.mark), [("ORDER_CONFIRMED", "ORDER_VERIFIED")]
        )
        self.assertEqual(event.order_id, order.pk)
        self.assertEqual(event.actor_id, self.su.pk)
        line = line_for(event, StockPoolKind.BAG, product_packaging=self.pp1)
        self.assertEqual((line.d_reserved, line.d_on_hand, line.d_consumed), (4, None, None))
        self.assertEqual(
            {line.pool_kind for line in event.lines.all()},
            {StockPoolKind.BAG},
            "a reservation touches no other pool",
        )

        for label, release, detail in (
            ("unverify", partial(unverify_order, actor=self.su), "UNVERIFIED"),
            ("hold", partial(hold_order, actor=self.su), "HELD"),
            ("reject", partial(reject_order, actor=self.su), "REJECTED"),
        ):
            with self.subTest(release=label):
                if order.status.code != "CONFIRMED":
                    verify_order(order, self.su)
                before = self.marker()
                release(order)
                self.assertEqual(
                    self.kinds_since(before), [("ORDER_RELEASED", detail)]
                )
                line = line_for(
                    self.events_since(before)[0],
                    StockPoolKind.BAG,
                    product_packaging=self.pp1,
                )
                self.assertEqual(line.d_reserved, -4)

    def test_partial_dispatch_revert_and_redispatch(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_partial_dispatch_revert_and_redispatch"""
        order = self.order(self.pp1, 4)
        before = self.marker()

        self.dispatch(order, self.pp1, shipped=3)
        [event] = self.events_since(before)
        self.assertEqual(self.kinds_since(before), [("ORDER_DISPATCHED", "PARTIAL")])
        line = line_for(event, StockPoolKind.BAG)
        # 4 reserved -> 1 reserved (the unshipped gap) + 3 consumed.
        self.assertEqual((line.d_reserved, line.d_consumed), (-3, 3))

        before = self.marker()
        revert_dispatch(order, actor=self.su)
        self.assertEqual(self.kinds_since(before), [("DISPATCH_REVERTED", "NONE")])
        line = line_for(self.events_since(before)[0], StockPoolKind.BAG)
        self.assertEqual((line.d_reserved, line.d_consumed), (3, -3))

        before = self.marker()
        self.dispatch(order, self.pp1)
        self.assertEqual(self.kinds_since(before), [("ORDER_DISPATCHED", "FULL")])

    def test_delivery_writes_no_event(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_delivery_writes_no_event"""
        order = self.order(self.pp1, 2)
        self.dispatch(order, self.pp1)
        before = self.marker()
        mark_delivered(order, actor=self.su)
        self.assertEqual(self.kinds_since(before), [])

    def test_editing_a_confirmed_order_is_recorded_and_an_unverified_one_is_not(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_editing_a_confirmed_order_is_recorded_and_an_unverified_one_is_not"""
        draft = self.order(self.pp1, 2, verify=False)
        sync_order_items(draft, [{"product_packaging": self.pp1, "quantity": 5}], self.su)
        self.assertEqual(self.kinds_since(self.mark), [], "a draft reserves nothing")

        order = self.order(self.pp1, 2)
        before = self.marker()
        sync_order_items(order, [{"product_packaging": self.pp1, "quantity": 6}], self.su)
        self.assertEqual(
            self.kinds_since(before), [("ORDER_EDITED", "ORDER_LINES_CHANGED")]
        )
        line = line_for(self.events_since(before)[0], StockPoolKind.BAG)
        self.assertEqual(line.d_reserved, 4)

    def test_custom_order_create_dispatch_revert_and_withdraw(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_custom_order_create_dispatch_revert_and_withdraw"""
        self.count_loose(self.product, 100)
        before = self.marker()
        order = self.custom_order(self.product, 30)
        self.assertEqual(
            self.kinds_since(before), [("ORDER_CONFIRMED", "CUSTOM_ORDER_CREATED")]
        )
        event = self.events_since(before)[0]
        self.assertEqual(event.custom_order_id, order.pk)
        line = line_for(event, StockPoolKind.LOOSE, packet_weight=W1)
        self.assertEqual(line.d_reserved, 30)

        before = self.marker()
        self.dispatch_custom(order, self.product)
        self.assertEqual(self.kinds_since(before), [("ORDER_DISPATCHED", "FULL")])
        line = line_for(self.events_since(before)[0], StockPoolKind.LOOSE)
        self.assertEqual((line.d_reserved, line.d_consumed), (-30, 30))

        before = self.marker()
        revert_custom(order)
        self.assertEqual(self.kinds_since(before), [("DISPATCH_REVERTED", "NONE")])

        before = self.marker()
        delete_custom_order(order, self.su)
        self.assertEqual(
            self.kinds_since(before), [("ORDER_RELEASED", "CUSTOM_ORDER_WITHDRAWN")]
        )

    # -- inward and waste ------------------------------------------------------------

    def test_every_raw_lot_transition(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_every_raw_lot_transition"""
        today = datetime.date.today()
        lot = InwardOperations.create_raw_lot(
            product=self.product, party=self.party, lot_no="L-1",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("40.000"), lab_sampling_date=today, actor=self.su,
        )
        self.assertEqual(self.kinds_since(self.mark), [], "a lot in Lab Testing moves nothing")

        def move(code, expected_detail, raw_deltas):
            before = self.marker()
            InwardOperations.update_raw_lot(
                lot,
                {
                    "status": Status.objects.get(code=code),
                    "effective_date": today if code != "LAB_TESTING" else None,
                },
                self.su,
            )
            [event] = self.events_since(before)
            self.assertEqual(
                self.kinds_since(before), [("INWARD_OPERATIONS", expected_detail)]
            )
            self.assertEqual(event.inward_raw_material_id, lot.pk)
            line = line_for(event, StockPoolKind.RAW)
            self.assertEqual(
                (line.d_incoming, line.d_rejected), raw_deltas, code
            )

        move("IN_USE", "RAW_LOT_IN_USE", (Decimal("40"), None))
        move("LAB_TESTING", "RAW_LOT_BACK_TO_LAB", (Decimal("-40"), None))
        move("RAW_MATERIAL_REJECTED", "RAW_LOT_REJECTED", (None, Decimal("40")))
        move("LAB_TESTING", "RAW_LOT_BACK_TO_LAB", (None, Decimal("-40")))
        move("IN_USE", "RAW_LOT_IN_USE", (Decimal("40"), None))

        before = self.marker()
        lot.mark_deleted(self.su)
        self.assertEqual(
            self.kinds_since(before), [("INWARD_OPERATIONS", "RAW_LOT_DELETED")]
        )
        line = line_for(self.events_since(before)[0], StockPoolKind.RAW)
        self.assertEqual(line.d_incoming, Decimal("-40"))
        self.assertEqual(self.events_since(before)[0].actor_id, self.su.pk)

    def test_a_shared_material_lot_is_recorded_once_and_listed_for_both_products(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_a_shared_material_lot_is_recorded_once_and_listed_for_both_products"""
        before = self.marker()
        lot = self.pouches("500", recipe=self.recipe_q)
        events = self.events_since(before)
        self.assertEqual(
            [(event.product_id, event.inward_other_material_id) for event in events],
            [(self.other_product.pk, lot.pk)],
            "a pool-wide incoming figure is recorded once, on the booking product",
        )
        self.assertEqual(
            line_for(events[0], StockPoolKind.OTHER, material_type=self.pouch).d_incoming,
            Decimal("500"),
        )

        before = self.marker()
        lot.mark_deleted(self.su)
        self.assertEqual(
            self.kinds_since(before), [("INWARD_OPERATIONS", "OTHER_MATERIAL_DELETED")]
        )

    def test_waste_recorded_and_deleted(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_waste_recorded_and_deleted"""
        before = self.marker()
        waste = inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("15"), reason="spill", actor=self.su
        )
        self.assertEqual(self.kinds_since(before), [("RAW_WASTED", "WASTE_RECORDED")])
        event = self.events_since(before)[0]
        self.assertEqual(event.raw_material_waste_id, waste.pk)
        self.assertEqual(line_for(event, StockPoolKind.RAW).d_wasted, Decimal("15"))

        before = self.marker()
        waste.mark_deleted(self.su)
        self.assertEqual(self.kinds_since(before), [("RAW_WASTED", "WASTE_DELETED")])
        self.assertEqual(
            line_for(self.events_since(before)[0], StockPoolKind.RAW).d_wasted,
            Decimal("-15"),
        )

    def test_waste_edited_records_the_difference(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_waste_edited_records_the_difference"""
        waste = inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("15"), reason="spill", actor=self.su
        )

        before = self.marker()
        inv.update_raw_waste(waste, actor=self.su, quantity_kg=Decimal("20"))
        self.assertEqual(self.kinds_since(before), [("RAW_WASTED", "WASTE_EDITED")])
        event = self.events_since(before)[0]
        self.assertEqual(event.raw_material_waste_id, waste.pk)
        self.assertEqual(line_for(event, StockPoolKind.RAW).d_wasted, Decimal("5"))

        before = self.marker()
        inv.update_raw_waste(waste, actor=self.su, quantity_kg=Decimal("8"))
        self.assertEqual(
            line_for(self.events_since(before)[0], StockPoolKind.RAW).d_wasted, Decimal("-12")
        )

        before = self.marker()
        inv.update_raw_waste(waste, actor=self.su, reason="rain")
        self.assertEqual(self.kinds_since(before), [])

    # -- counts ----------------------------------------------------------------------

    def test_count_classification_and_deletion(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_count_classification_and_deletion"""
        before = self.marker()
        self.count_bags({self.pp1: 60})
        self.assertEqual(self.kinds_since(before), [("PACKED", "BAG_COUNT")])

        before = self.marker()
        self.count_bags({self.pp1: 45})
        self.assertEqual(self.kinds_since(before), [("STOCK_ADJUSTED", "BAG_COUNT")])

        before = self.marker()
        self.count_loose(self.product, 12)
        self.assertEqual(self.kinds_since(before), [("PACKED", "LOOSE_COUNT")])

        before = self.marker()
        snapshot = InventorySnapshot.objects.get(
            product_packaging=self.pp1, snapshot_date=inv.latest_snapshot_date()
        )
        snapshot.mark_deleted(self.su)
        self.assertEqual(self.kinds_since(before), [("STOCK_ADJUSTED", "COUNT_DELETED")])
        self.assertEqual(self.events_since(before)[0].inventory_snapshot_id, snapshot.pk)

    def test_a_recount_that_finds_the_same_stock_writes_nothing(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_a_recount_that_finds_the_same_stock_writes_nothing"""
        before = self.marker()
        self.count_bags({self.pp1: 50})
        self.assertEqual(self.kinds_since(before), [])

    def test_untouched_pools_get_no_line_and_other_products_no_event(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_untouched_pools_get_no_line_and_other_products_no_event"""
        before = self.marker()
        self.count_bags({self.pp1: 70})
        events = self.events_since(before)
        self.assertEqual({event.product_id for event in events}, {self.product.pk})
        [event] = events
        self.assertEqual(
            {line.pool_kind for line in event.lines.all()},
            {StockPoolKind.BAG, StockPoolKind.RAW, StockPoolKind.OTHER},
        )
        self.assertEqual(
            line_for(event, StockPoolKind.BAG).d_on_hand, Decimal("20"), "70 - 50"
        )
        # 20 bags x 20 packets x 1kg; and one pouch a packet.
        self.assertEqual(line_for(event, StockPoolKind.RAW).d_packed, Decimal("400"))
        self.assertEqual(
            line_for(event, StockPoolKind.OTHER, material_type=self.pouch).d_packed,
            Decimal("400"),
        )

    def test_one_write_can_raise_lower_and_reset_pools_of_one_product(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_one_write_can_raise_lower_and_reset_pools_of_one_product"""
        pp_b = add_packaging(self.product, packet_weight=Decimal("2.000"), packets=10, actor=self.su)
        pp_c = add_packaging(self.product, packet_weight=Decimal("3.000"), packets=10, actor=self.su)
        self.count_everything({self.pp1: 50, self.qq1: 50, pp_b: 10, pp_c: 10})
        # pp_c's dispatched bags precede the next count, so recounting it lower by
        # exactly what left changes on_hand and consumed but not what was packed.
        order = self.order(pp_c, 4)
        self.dispatch(order, pp_c)
        before = self.marker()
        self.count_bags(
            {self.pp1: 55, pp_b: 5, pp_c: 6}, day=datetime.date.today() + datetime.timedelta(days=1)
        )
        kinds = sorted(
            kind for kind in self.kinds_since(before, self.product)
        )
        self.assertEqual(
            kinds,
            [
                ("PACKED", "BAG_COUNT"),
                ("STOCK_ADJUSTED", "BAG_COUNT"),
                ("STOCK_COUNTED", "BAG_COUNT"),
            ],
        )

    def test_a_failed_write_leaves_no_ledger_rows(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_a_failed_write_leaves_no_ledger_rows"""
        total = StockEvent.objects.count()
        with self.assertRaises(ValueError):
            self.count_bags({self.pp1: 10_000_000})
        with self.assertRaises(ValueError):
            inv.record_raw_waste(
                product=self.product, quantity_kg=Decimal("5000000"), reason="x", actor=self.su
            )
        self.assertEqual(StockEvent.objects.count(), total)

    def test_every_stored_detail_is_legal_for_its_event_type(self):
        """tests/test_stock_ledger_operations.py::StockLedgerOperationsTest::test_every_stored_detail_is_legal_for_its_event_type"""
        order = self.order(self.pp1, 3)
        self.dispatch(order, self.pp1, shipped=2)
        revert_dispatch(order, actor=self.su)
        self.count_bags({self.pp1: 40})
        self.pouches("10")
        inv.record_raw_waste(product=self.product, quantity_kg=Decimal("1"), reason="", actor=self.su)
        self.assertTrue(StockEvent.objects.exists())
        for event in StockEvent.objects.all():
            with self.subTest(event=str(event)):
                self.assertIn(event.detail, VALID_DETAILS[event.event_type])
