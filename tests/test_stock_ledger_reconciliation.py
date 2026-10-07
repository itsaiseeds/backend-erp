"""Randomised reconciliation: the ledger must equal the live figures after every write.

A seeded-random sequence of 200 operations runs through the real operation
functions -- inward lots, counts, orders, dispatches, reverts, waste, custom
orders, return orders (raise, accept, revert, reject, unreject), recipe changes,
deletions, and the passing of days. After **every** step
the ledger totals are compared with the live figures of every pool of every
product (``StockLedgerOperations.check_ledger``). At the end the report itself is
checked: each row plus the next row's change is the next row, a range's closing
balance is the next range's opening balance, and the shared packing material
reconciles on every row.

Operations that the system rightly refuses (a shortfall, a wrong status) are
skipped; refusing must also leave the ledger untouched, which the per-step check
proves.

Run: bash scripts/run.sh test-serial tests/test_stock_ledger_reconciliation.py
"""

from __future__ import annotations

import datetime
import random
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations, StockLedgerOperations
from aggregator.CustomOrderOperations import delete_custom_order
from aggregator.CustomOrderOperations import revert_dispatch as revert_custom
from aggregator.models import (
    InventorySnapshot,
    OtherMaterialRecipe,
    ProductPackaging,
    Status,
    StatusIds,
    StockEvent,
    StockEventType,
)
from aggregator.OrderOperations import (
    hold_order,
    mark_delivered,
    reject_order,
    revert_dispatch,
    sync_order_items,
    unverify_order,
)
from aggregator.ReturnOrderOperations import (
    accept_return_order,
    create_return_order,
    reject_return_order,
    revert_accept_return_order,
    unreject_return_order,
)
from aggregator.StockLedgerReport import product_ledger_rows
from tests.common import lab_verdict
from tests.stock_ledger_support import TODAY, W1, LedgerWorldTestCase

OPERATIONS = 200
SEED = 20261003
REFUSALS = (ValidationError, ValueError, PermissionDenied)
RECONCILED_FIELDS = ("on_hand", "reserved", "consumed", "available")


def flat(row):
    """Every numeric figure of a report row, keyed by where it lives."""
    figures = {}
    for pool in row["bag_pools"]:
        for name in RECONCILED_FIELDS:
            figures[("bag", pool["packaging"]["public_id"], name)] = pool[name]
    for pool in row["packet_pools"]:
        for name in RECONCILED_FIELDS:
            figures[("loose", pool["packet_weight"], name)] = pool[name]
    for name in ("incoming", "packed", "rejected", "wasted", "available"):
        figures[("raw", name)] = Decimal(row["raw_material"][name])
    for material in row["other_materials"]:
        for name in ("incoming", "packed"):
            figures[("other", material["material_type"]["id"], name)] = Decimal(material[name])
    return figures


def flat_change(row):
    figures = {}
    for pool in row["bag_pools"]:
        for name in RECONCILED_FIELDS:
            figures[("bag", pool["packaging"]["public_id"], name)] = pool["change"][name]
    for pool in row["packet_pools"]:
        for name in RECONCILED_FIELDS:
            figures[("loose", pool["packet_weight"], name)] = pool["change"][name]
    for name in ("incoming", "packed", "rejected", "wasted", "available"):
        figures[("raw", name)] = Decimal(row["raw_material"]["change"][name])
    for material in row["other_materials"]:
        for name in ("incoming", "packed"):
            figures[("other", material["material_type"]["id"], name)] = Decimal(
                material["change"][name]
            )
    return figures


class StockLedgerReconciliationTest(LedgerWorldTestCase):
    def test_two_hundred_random_operations_keep_the_ledger_equal_to_live(self):
        """tests/test_stock_ledger_reconciliation.py::StockLedgerReconciliationTest::test_two_hundred_random_operations_keep_the_ledger_equal_to_live"""
        rng = random.Random(SEED)  # noqa: S311 -- a reproducible test sequence, not security
        StockLedgerOperations.seed_ledger()
        self.sim_day = TODAY
        self.last_event = 0
        self.lots = []
        self.orders = []
        self.custom_orders = []
        self.wastes = []
        self.returns = []
        self.counts_needed_in_full = True
        applied = 0

        operations = [
            self.op_raw_in, self.op_raw_in, self.op_lot_move, self.op_pouches,
            self.op_bag_count, self.op_bag_count, self.op_loose_count, self.op_new_day,
            self.op_order, self.op_order, self.op_dispatch, self.op_revert, self.op_release,
            self.op_edit, self.op_deliver, self.op_custom, self.op_custom_dispatch,
            self.op_custom_release, self.op_waste, self.op_waste_delete, self.op_recipe,
            self.op_delete_count, self.op_delete_lot,
            self.op_return_create, self.op_return_create, self.op_return_accept,
            self.op_return_accept, self.op_return_revert_accept, self.op_return_reject,
            self.op_return_unreject,
        ]
        # Stock first, so most later operations have something to act on.
        self.op_raw_in(rng)
        self.op_raw_in(rng)
        self.op_pouches(rng)
        self.op_new_day(rng, advance=False)

        for index in range(OPERATIONS):
            operation = rng.choice(operations)
            try:
                if operation(rng) is not False:
                    applied += 1
            except REFUSALS:
                pass
            self._stamp(index)
            self.assertEqual(
                StockLedgerOperations.check_ledger(),
                [],
                f"step {index}: {operation.__name__} left the ledger out of step",
            )

        self.assertGreater(applied, OPERATIONS // 3, "too few operations took effect")
        self.assertGreater(StockEvent.objects.count(), 40)
        self.assertTrue(
            StockEvent.objects.filter(event_type=StockEventType.RETURN_OPERATIONS).exists(),
            "the sequence never accepted a return",
        )
        self._assert_reports_reconcile()

    # -- stamping ----------------------------------------------------------------

    def _stamp(self, index):
        """Spread events over simulated days so ranges and balances can be compared."""
        moment = datetime.datetime.combine(
            self.sim_day, datetime.time(8, 0), tzinfo=datetime.datetime.now().astimezone().tzinfo
        ) + datetime.timedelta(minutes=index)
        StockEvent.objects.filter(pk__gt=self.last_event).update(occurred_at=moment)
        self.last_event = StockEvent.objects.order_by("-pk").values_list("pk", flat=True).first() or 0

    # -- operations ----------------------------------------------------------------

    def _product(self, rng):
        return rng.choice([self.product, self.other_product])

    def _packaging(self, rng):
        return rng.choice([self.pp1, self.qq1])

    def op_raw_in(self, rng):
        self.lots.append(self.raw(self._product(rng), str(rng.randint(50, 600))))

    def op_lot_move(self, rng):
        if not self.lots:
            return False
        lot = rng.choice(self.lots)
        lot.refresh_from_db()
        current = InwardOperations.raw_status_of(lot)
        lab_testing = InwardOperations.InwardRawMaterialStatus.LAB_TESTING
        if current == lab_testing:
            # Only a lab tester's verdict leaves Lab Testing (Pass -> In Use, Fail -> Rejected).
            lab_verdict(lot.public_id, rng.choice(["Pass", "Fail"]), actor=self.su)
            return
        # An In Use / Rejected lot can only be sent back to Lab Testing, by an admin.
        InwardOperations.assert_raw_status_transition(current, lab_testing)
        InwardOperations.update_raw_lot(
            lot,
            {"status": Status.objects.get(code="LAB_TESTING"), "effective_date": None},
            self.su,
        )

    def op_pouches(self, rng):
        self.pouches(str(rng.randint(100, 900)), recipe=rng.choice([self.recipe_p, self.recipe_q]))

    def op_bag_count(self, rng):
        packaging = self._packaging(rng)
        bags = rng.randint(0, 40)
        if self.counts_needed_in_full:
            self.count_everything({packaging: bags}, day=self.sim_day)
            self.counts_needed_in_full = False
        else:
            self.count_bags(
                {packaging: bags}, day=self.sim_day, carry_forward=rng.random() < 0.7
            )

    def op_loose_count(self, rng):
        self.count_loose(
            self._product(rng), rng.randint(0, 60), day=self.sim_day,
            carry_forward=rng.random() < 0.7,
        )

    def op_new_day(self, rng, advance=True):
        if advance:
            self.sim_day += datetime.timedelta(days=1)
        self.counts_needed_in_full = True

    def op_order(self, rng):
        packaging = self._packaging(rng)
        self.orders.append((self.order(packaging, rng.randint(1, 5)), packaging))

    def _pick(self, rng, status_codes):
        candidates = []
        for order, packaging in self.orders:
            order.refresh_from_db()
            if order.status.code in status_codes:
                candidates.append((order, packaging))
        return rng.choice(candidates) if candidates else None

    def op_dispatch(self, rng):
        picked = self._pick(rng, {"CONFIRMED"})
        if picked is None:
            return False
        order, packaging = picked
        quantity = order.items.get().quantity
        self.dispatch(order, packaging, shipped=rng.randint(0, quantity))

    def op_revert(self, rng):
        picked = self._pick(rng, {"DISPATCHED"})
        if picked is None:
            return False
        revert_dispatch(picked[0], actor=self.su)

    def op_release(self, rng):
        picked = self._pick(rng, {"CONFIRMED"})
        if picked is None:
            return False
        release = rng.choice([hold_order, unverify_order, reject_order])
        release(picked[0], actor=self.su)

    def op_edit(self, rng):
        picked = self._pick(rng, {"CONFIRMED", "BOOKED"})
        if picked is None:
            return False
        order, packaging = picked
        sync_order_items(
            order, [{"product_packaging": packaging, "quantity": rng.randint(1, 8)}], self.su
        )

    def op_deliver(self, rng):
        picked = self._pick(rng, {"DISPATCHED"})
        if picked is None:
            return False
        mark_delivered(picked[0], actor=self.su)

    def op_custom(self, rng):
        product = self._product(rng)
        self.custom_orders.append((self.custom_order(product, rng.randint(1, 12)), product))

    def _pick_custom(self, rng, status_codes):
        candidates = []
        for order, product in self.custom_orders:
            order.refresh_from_db()
            if not order.is_deleted and order.status.code in status_codes:
                candidates.append((order, product))
        return rng.choice(candidates) if candidates else None

    def op_custom_dispatch(self, rng):
        picked = self._pick_custom(rng, {"CONFIRMED"})
        if picked is None:
            picked = self._pick_custom(rng, {"DISPATCHED"})
            if picked is None:
                return False
            revert_custom(picked[0])
            return None
        self.dispatch_custom(*picked)

    def op_custom_release(self, rng):
        picked = self._pick_custom(rng, {"CONFIRMED"})
        if picked is None:
            return False
        delete_custom_order(picked[0], self.su)

    def op_waste(self, rng):
        self.wastes.append(
            inv.record_raw_waste(
                product=self._product(rng),
                quantity_kg=Decimal(rng.randint(1, 40)),
                reason="spill",
                actor=self.su,
            )
        )

    def op_waste_delete(self, rng):
        live = [waste for waste in self.wastes if not waste.is_deleted]
        if not live:
            return False
        waste = rng.choice(live)
        waste.refresh_from_db()
        waste.mark_deleted(self.su)

    def op_recipe(self, rng):
        recipe = rng.choice([self.recipe_p, self.recipe_q])
        recipe.refresh_from_db()
        if recipe.is_deleted:
            return False
        recipe.mark_deleted(self.su)
        replacement = OtherMaterialRecipe.objects.create(
            product=recipe.product, material_type=recipe.material_type,
            packet_weight=W1, quantity=Decimal(rng.randint(1, 3)), created_by=self.su,
        )
        if recipe == self.recipe_p:
            self.recipe_p = replacement
        else:
            self.recipe_q = replacement

    def op_delete_count(self, rng):
        row = (
            InventorySnapshot.objects.filter(product_packaging=self._packaging(rng))
            .order_by("-snapshot_date")
            .first()
        )
        if row is None:
            return False
        row.mark_deleted(self.su)

    def op_delete_lot(self, rng):
        if not self.lots:
            return False
        lot = rng.choice(self.lots)
        lot.refresh_from_db()
        if lot.is_deleted:
            return False
        lot.mark_deleted(self.su)

    def op_return_create(self, rng):
        picked = self._pick(rng, {"DISPATCHED", "DELIVERED"})
        if picked is None:
            return False
        order, packaging = picked
        self.returns.append(
            create_return_order(
                order,
                return_date=None,
                items=[
                    {
                        "product": packaging.product,
                        "packet_weight": packaging.packet_weight,
                        "packets": rng.randint(1, 30),
                        "price_per_packet": Decimal("5.00"),
                    }
                ],
                actor=self.sp_user,
            )
        )

    def _pick_return(self, rng, status_id):
        candidates = []
        for ret in self.returns:
            ret.refresh_from_db()
            if ret.status_id == status_id:
                candidates.append(ret)
        return rng.choice(candidates) if candidates else None

    def op_return_accept(self, rng):
        ret = self._pick_return(rng, StatusIds.RETURN_PENDING)
        if ret is None:
            return False
        include = rng.random() < 0.6
        recipe = self.recipe_p if ret.items.get().product_id == self.product.pk else self.recipe_q
        accept_return_order(
            ret,
            include_other=include,
            recipe_public_ids=[recipe.public_id] if include else None,
            admin=self.su,
        )

    def op_return_revert_accept(self, rng):
        ret = self._pick_return(rng, StatusIds.RETURN_ACCEPTED)
        if ret is None:
            return False
        revert_accept_return_order(ret, admin=self.su)

    def op_return_reject(self, rng):
        ret = self._pick_return(rng, StatusIds.RETURN_PENDING)
        if ret is None:
            return False
        reject_return_order(ret, admin=self.su)

    def op_return_unreject(self, rng):
        ret = self._pick_return(rng, StatusIds.RETURN_REJECTED)
        if ret is None:
            return False
        unreject_return_order(ret, admin=self.su)

    # -- the report ------------------------------------------------------------------

    def _assert_reports_reconcile(self):
        last_day = self.sim_day
        for product in (self.product, self.other_product):
            rows = product_ledger_rows(product, TODAY, last_day)
            self.assertEqual(rows[0]["event"], "OPENING_BALANCE")
            self.assertEqual(rows[-1]["event"], "CLOSING_BALANCE")
            for before, after in zip(rows, rows[1:-1], strict=False):
                now, then, delta = flat(before), flat(after), flat_change(after)
                for key in now:
                    with self.subTest(product=product.name, at=after["occurred_at"], key=key):
                        self.assertEqual(then[key] - now[key], delta[key])
            for row in rows:
                for material in row["other_materials"]:
                    self.assertEqual(
                        Decimal(material["incoming"])
                        - Decimal(material["packed"])
                        - Decimal(material["used_by_other_products"]),
                        Decimal(material["available"]),
                    )
            # The window's closing balance is the next window's opening balance.
            day = TODAY
            while day < last_day:
                closing = product_ledger_rows(product, TODAY, day)[-1]
                opening = product_ledger_rows(product, day + datetime.timedelta(days=1), last_day)[0]
                self.assertEqual(flat(closing), flat(opening), f"{product.name} at {day}")
                day += datetime.timedelta(days=1)
            # And the whole range closes on the live position.
            final = flat(rows[-1])
            live = StockLedgerOperations.read_positions([product.pk])[product.pk]
            self.assertEqual(final[("raw", "incoming")], live[(3, 0)]["incoming"])
            self.assertEqual(final[("raw", "wasted")], live[(3, 0)]["wasted"])
        self.assertTrue(ProductPackaging.objects.filter(pk=self.pp1.pk).exists())
