"""Return orders: goods a client sends back against an order already shipped.

Covers ``aggregator/ReturnOrderOperations.py`` and the endpoints built on it
(``docs/prd/return-orders.md``): the limit and one-live-return rules, the
lifecycle (accept / reject / unreject / revert-accept), the inward stock an
accept books, and what stays refused afterwards.

Every write goes through the real operations layer, so the stock ledger records
it; the autouse guard in ``tests/common.py`` asserts the ledger equals the live
figures when each test ends. Authentication and role gating live in
``tests/test_view_contracts.py``.

Run: bash scripts/run.sh test-serial tests/test_return_orders.py
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations, StockLedgerOperations
from aggregator.models import (
    InwardOtherMaterial,
    InwardRawMaterial,
    OtherMaterialRecipe,
    Product,
    ReturnOrder,
    ReturnOrderItem,
    StatusIds,
    StockEvent,
    StockEventLine,
    StockPoolKind,
)
from aggregator.OrderOperations import (
    create_order,
    dispatch_order,
    mark_delivered,
    revert_dispatch,
    verify_order,
)
from aggregator.ReturnOrderOperations import (
    accept_return_order,
    create_return_order,
    reject_return_order,
    return_order_payload,
    return_order_recipe_options,
    revert_accept_return_order,
    unreject_return_order,
    update_return_order,
)
from aggregator.StockLedgerReport import product_ledger_rows
from api.return_order_serializers import (
    ReturnOrderListItemSerializer,
    ReturnOrderPayloadSerializer,
    ReturnOrderPrefillSerializer,
    ReturnOrderRecipesSerializer,
)
from api.sales_admin.ExportInwardEntriesView import ExportInwardEntriesResponseSerializer
from authentication.models import Admin, SalesPerson, User
from tests.stock_ledger_support import TODAY, W1, LedgerWorldTestCase
from tests.test_stock_ledger_api import documented_keys_mismatches
from tests.test_stock_ledger_operations import line_for

W2 = Decimal("2.000")


class ReturnWorldTestCase(LedgerWorldTestCase):
    """The ledger world plus a sales admin, a second sales person and stock to ship."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin_user = User.objects.create_user(
            "9530000001", "Return Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.su, can_update_stock_count=True)
        cls.other_sp = User.objects.create_user(
            "9530000002", "Other Sales", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        SalesPerson.objects.create(user=cls.other_sp, city=cls.city, created_by=cls.su)

    def setUp(self):
        super().setUp()
        self.raw(self.product, "100000")
        self.raw(self.other_product, "100000")
        self.pouches("100000")
        # A complete count: orders can only be verified against a full one.
        self.count_everything({self.pp1: 50, self.qq1: 50})

    # -- builders ----------------------------------------------------------------

    def dispatched_order(self, lines=None, *, actor=None):
        """A DISPATCHED order shipping ``{packaging: bags}`` (default 2 bags of P)."""
        lines = lines or {self.pp1: 2}
        order = create_order(
            client=self.client_obj,
            delivery_address=self.address,
            actor=actor or self.sp_user,
            items=[{"product_packaging": p, "quantity": q} for p, q in lines.items()],
        )
        verify_order(order, self.su)
        dispatch_order(
            order,
            actor=self.su,
            from_city=self.city,
            driver_name="Ramesh",
            driver_number="9876500009",
            vehicle_number="GJ05AB1234",
            lot_numbers={p.public_id: "LOT-1" for p in lines},
        )
        order.refresh_from_db()
        return order

    def item(self, product, packets, *, weight=W1, price="5.00"):
        return {
            "product": product,
            "packet_weight": weight,
            "packets": packets,
            "price_per_packet": Decimal(price),
        }

    def new_return(self, order, packets=10, *, product=None, actor=None):
        return create_return_order(
            order,
            return_date=None,
            items=[self.item(product or self.product, packets)],
            actor=actor or self.sp_user,
        )

    def accept(self, ret, *, recipes=None):
        return accept_return_order(
            ret,
            include_other=recipes is not None,
            recipe_public_ids=[recipe.public_id for recipe in recipes] if recipes else None,
            admin=self.admin_user,
        )

    def pouch_inward(self):
        return inv.other_material_inward([self.pouch.id]).get(self.pouch.id, Decimal("0"))

    def replace_recipe_p(self, quantity="3.000"):
        """Soft-delete ``recipe_p`` and create its live replacement."""
        self.recipe_p.mark_deleted(self.su)
        return OtherMaterialRecipe.objects.create(
            product=self.product,
            material_type=self.pouch,
            packet_weight=W1,
            quantity=Decimal(quantity),
            created_by=self.su,
        )


class ReturnOrderOperationsTest(ReturnWorldTestCase):
    """The operations layer: rules, lifecycle, stock and ledger.

    tests/test_return_orders.py::ReturnOrderOperationsTest
    """

    def test_a_return_is_refused_beyond_what_the_challan_carried(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_a_return_is_refused_beyond_what_the_challan_carried"""
        order = self.dispatched_order()  # 2 bags x 20 packets = 40 packets of P, 1kg
        cases = [
            ("over the limit", [self.item(self.product, 41)]),
            ("wrong packet weight", [self.item(self.product, 1, weight=W2)]),
            ("a product not on the challan", [self.item(self.other_product, 1)]),
            ("no items", []),
            ("the same pair twice", [self.item(self.product, 5), self.item(self.product, 5)]),
        ]
        for label, items in cases:
            with self.subTest(case=label), self.assertRaises(ValidationError):
                create_return_order(order, return_date=None, items=items, actor=self.sp_user)
        self.assertFalse(ReturnOrder.all_objects.exists())

        # Exactly the limit is fine.
        ret = create_return_order(
            order, return_date=None, items=[self.item(self.product, 40)], actor=self.sp_user
        )
        self.assertEqual(ret.status_id, StatusIds.RETURN_PENDING)
        self.assertEqual(ret.return_date, TODAY)

    def test_only_a_dispatched_or_delivered_order_can_have_a_return(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_only_a_dispatched_or_delivered_order_can_have_a_return"""
        confirmed = self.order(self.pp1, 2)
        booked = self.order(self.pp1, 1, verify=False)
        for label, order in (("CONFIRMED", confirmed), ("BOOKED", booked)):
            with self.subTest(status=label), self.assertRaises(ValidationError):
                self.new_return(order)

        delivered = self.dispatched_order()
        mark_delivered(delivered)
        ret = self.new_return(delivered)
        self.assertEqual(ret.order_id, delivered.pk)

    def test_one_live_return_per_order_and_a_rejected_one_does_not_count(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_one_live_return_per_order_and_a_rejected_one_does_not_count"""
        order = self.dispatched_order()
        first = self.new_return(order, 10)
        with self.assertRaises(ValidationError):
            self.new_return(order, 5)

        # Rejected: out of the way, and its packets are free again.
        reject_return_order(first, admin=self.admin_user)
        second = self.new_return(order, 40)

        with self.subTest(case="unreject while another return is live"):
            with self.assertRaises(ValidationError):
                unreject_return_order(first, admin=self.admin_user)
            first.refresh_from_db()
            self.assertEqual(first.status_id, StatusIds.RETURN_REJECTED)

        reject_return_order(second, admin=self.admin_user)
        unreject_return_order(first, admin=self.admin_user)
        first.refresh_from_db()
        self.assertEqual(first.status_id, StatusIds.RETURN_PENDING)
        self.assertIsNone(first.rejected_by_id)

        with self.subTest(case="unreject re-checks the limit"):
            reject_return_order(first, admin=self.admin_user)
            # The items no longer fit the challan's 40 packets (no stock involved).
            ReturnOrderItem.objects.filter(return_order=first).update(packets=41)
            with self.assertRaises(ValidationError):
                unreject_return_order(first, admin=self.admin_user)
            first.refresh_from_db()
            self.assertEqual(first.status_id, StatusIds.RETURN_REJECTED)

    def test_accept_books_the_raw_kilograms_as_inward_stock(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_accept_books_the_raw_kilograms_as_inward_stock"""
        order = self.dispatched_order()
        ret = self.new_return(order, 10)
        incoming = inv.raw_inward_kg(self.product)
        mark = self.marker()
        self.assertEqual(self.kinds_since(mark), [], "raising a return moves no stock")

        self.accept(ret)

        self.assertEqual(inv.raw_inward_kg(self.product), incoming + 10)
        self.assertEqual(self.kinds_since(mark), [("RETURN_OPERATIONS", "RETURN_ACCEPTED")])
        [event] = self.events_since(mark)
        self.assertEqual(event.return_order_id, ret.pk)
        self.assertEqual(event.actor_id, self.admin_user.pk)
        self.assertEqual(line_for(event, StockPoolKind.RAW).d_incoming, 10)
        self.assertFalse(
            [line for line in event.lines.all() if line.pool_kind == StockPoolKind.OTHER]
        )

        lot = InwardRawMaterial.objects.get(return_order=ret)
        self.assertIsNone(lot.party_id)
        self.assertEqual(lot.lot_no, ret.public_id)
        self.assertEqual(lot.status_id, StatusIds.IN_USE)
        self.assertEqual(lot.effective_date, inv.today())
        self.assertEqual(lot.quantity_kg, Decimal("10.000"))
        self.assertEqual(lot.created_by_id, self.admin_user.pk)
        self.assertFalse(InwardOtherMaterial.objects.filter(return_order=ret).exists())

        ret.refresh_from_db()
        self.assertEqual(ret.status_id, StatusIds.RETURN_ACCEPTED)
        self.assertIs(ret.include_in_other_raw_materials, False)
        self.assertEqual(ret.verified_by_id, self.admin_user.pk)
        self.assertIsNotNone(ret.verified_at)

    def test_accept_with_packing_materials_books_each_chosen_recipe(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_accept_with_packing_materials_books_each_chosen_recipe"""
        order = self.dispatched_order({self.pp1: 2, self.qq1: 3})
        ret = create_return_order(
            order,
            return_date=None,
            items=[self.item(self.product, 10), self.item(self.other_product, 5)],
            actor=self.sp_user,
        )
        pouches = self.pouch_inward()
        mark = self.marker()

        self.accept(ret, recipes=[self.recipe_p, self.recipe_q])

        # P: 10 packets x 1 pouch, Q: 5 packets x 2 pouches -- booked once per line.
        self.assertEqual(self.pouch_inward(), pouches + 20)
        quantities = {
            lot.recipe_id: lot.quantity
            for lot in InwardOtherMaterial.objects.filter(return_order=ret)
        }
        self.assertEqual(
            quantities,
            {self.recipe_p.pk: Decimal("10.000"), self.recipe_q.pk: Decimal("10.000")},
        )
        for lot in InwardOtherMaterial.objects.filter(return_order=ret):
            self.assertIsNone(lot.party_id)
            self.assertEqual(lot.effective_date, inv.today())

        # One event per product; the pool-wide pouch incoming is written once.
        self.assertEqual(
            sorted(self.kinds_since(mark)),
            [("RETURN_OPERATIONS", "RETURN_ACCEPTED")] * 2,
        )
        recorded = sum(
            line.d_incoming or 0
            for event in self.events_since(mark)
            for line in event.lines.all()
            if line.pool_kind == StockPoolKind.OTHER
        )
        self.assertEqual(recorded, 20)
        ret.refresh_from_db()
        self.assertIs(ret.include_in_other_raw_materials, True)

    def test_a_deleted_recipe_can_book_material_and_the_picker_lists_it(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_a_deleted_recipe_can_book_material_and_the_picker_lists_it"""
        order = self.dispatched_order()
        ret = self.new_return(order, 10)
        old = self.recipe_p
        live = self.replace_recipe_p("3.000")

        [line] = return_order_recipe_options(ret)
        self.assertEqual(line["packets"], 10)
        listed = {recipe["public_id"]: recipe["is_deleted"] for recipe in line["recipes"]}
        self.assertEqual(listed, {old.public_id: True, live.public_id: False})
        deleted = next(r for r in line["recipes"] if r["public_id"] == old.public_id)
        self.assertIsNotNone(deleted["deleted_at"])

        pouches = self.pouch_inward()
        self.accept(ret, recipes=[old])

        # The lot is booked against the deleted recipe, and still counts.
        self.assertEqual(self.pouch_inward(), pouches + 10)
        self.assertEqual(InwardOtherMaterial.objects.get(return_order=ret).recipe_id, old.pk)
        self.assertEqual(StockLedgerOperations.check_ledger(), [])

    def test_accept_refuses_bad_recipe_choices_and_writes_nothing(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_accept_refuses_bad_recipe_choices_and_writes_nothing"""
        order = self.dispatched_order({self.pp1: 2, self.qq1: 3})
        ret = create_return_order(
            order,
            return_date=None,
            items=[self.item(self.product, 10), self.item(self.other_product, 5)],
            actor=self.sp_user,
        )
        old = self.recipe_p
        live = self.replace_recipe_p("3.000")

        cases = [
            ("flag false with recipes", False, [live.public_id], "must be empty"),
            ("flag true with no recipes", True, [], "Not covered"),
            ("unknown recipe", True, ["OMR-NOSUCHRECIPE"], "Unknown recipe"),
            (
                "two recipes of one material type",
                True,
                [old.public_id, live.public_id, self.recipe_q.public_id],
                "at most one recipe per material type",
            ),
            ("an uncovered line", True, [live.public_id], "Not covered"),
        ]
        mark = self.marker()
        for label, include, ids, fragment in cases:
            with self.subTest(case=label):
                with self.assertRaises(ValidationError) as caught:
                    accept_return_order(
                        ret, include_other=include, recipe_public_ids=ids, admin=self.admin_user
                    )
                self.assertIn(fragment, " ".join(caught.exception.messages))
                ret.refresh_from_db()
                self.assertEqual(ret.status_id, StatusIds.RETURN_PENDING)
                self.assertFalse(InwardRawMaterial.objects.filter(return_order=ret).exists())
                self.assertFalse(InwardOtherMaterial.objects.filter(return_order=ret).exists())
                self.assertEqual(self.kinds_since(mark), [])

        # The uncovered message names the line that was left out.
        with self.assertRaises(ValidationError) as caught:
            self.accept(ret, recipes=[live])
        self.assertIn(self.other_product.name, " ".join(caught.exception.messages))

        # A recipe that matches no line of the return.
        order_p = self.dispatched_order()
        p_return = self.new_return(order_p, 5)
        with self.assertRaises(ValidationError) as caught:
            self.accept(p_return, recipes=[self.recipe_q])
        self.assertIn("match no line", " ".join(caught.exception.messages))

    def test_revert_accept_removes_the_lots_and_returns_to_pending(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_revert_accept_removes_the_lots_and_returns_to_pending"""
        order = self.dispatched_order()
        ret = self.new_return(order, 10)
        incoming, pouches = inv.raw_inward_kg(self.product), self.pouch_inward()
        self.accept(ret, recipes=[self.recipe_p])
        mark = self.marker()

        revert_accept_return_order(ret, admin=self.admin_user)

        self.assertEqual(inv.raw_inward_kg(self.product), incoming)
        self.assertEqual(self.pouch_inward(), pouches)
        self.assertFalse(InwardRawMaterial.objects.filter(return_order=ret).exists())
        self.assertFalse(InwardOtherMaterial.objects.filter(return_order=ret).exists())
        self.assertEqual(InwardRawMaterial.all_objects.filter(return_order=ret).count(), 1)
        self.assertTrue(
            InwardRawMaterial.all_objects.get(return_order=ret).is_deleted,
        )
        ret.refresh_from_db()
        self.assertEqual(ret.status_id, StatusIds.RETURN_PENDING)
        self.assertIsNone(ret.include_in_other_raw_materials)
        self.assertIsNone(ret.verified_by_id)
        self.assertIsNone(ret.verified_at)
        # One event, written once even though the lots were removed together.
        self.assertEqual(self.kinds_since(mark), [("RETURN_OPERATIONS", "RETURN_ACCEPT_REVERTED")])
        [event] = self.events_since(mark)
        self.assertEqual(line_for(event, StockPoolKind.RAW).d_incoming, -10)

        # Back to PENDING it can be accepted again.
        self.accept(ret)
        self.assertEqual(inv.raw_inward_kg(self.product), incoming + 10)

    def test_revert_accept_is_refused_once_the_stock_has_been_packed(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_revert_accept_is_refused_once_the_stock_has_been_packed"""
        self.pouches("1000000")
        order = self.dispatched_order()
        ret = self.new_return(order, 20)
        self.accept(ret)
        # Pack every kilogram P has (100000 + the 20 returned): 20 kg a bag, so
        # 5001 bags, of which 2 shipped before the count.
        self.count_everything({self.pp1: 4999, self.qq1: 50})
        self.assertEqual(inv.raw_available_kg(self.product), 0)
        mark = self.marker()

        with self.assertRaises(ValidationError) as caught:
            revert_accept_return_order(ret, admin=self.admin_user)

        self.assertIn("short by", " ".join(caught.exception.messages))
        ret.refresh_from_db()
        self.assertEqual(ret.status_id, StatusIds.RETURN_ACCEPTED)
        self.assertTrue(InwardRawMaterial.objects.filter(return_order=ret).exists())
        self.assertEqual(self.kinds_since(mark), [])

    def test_an_order_with_a_live_return_cannot_have_its_dispatch_reverted(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_an_order_with_a_live_return_cannot_have_its_dispatch_reverted"""
        order = self.dispatched_order()
        ret = self.new_return(order, 10)
        for label, prepare in (
            ("pending", lambda: None),
            (
                "accepted",
                lambda: (
                    reject_return_order(ret, admin=self.admin_user),
                    unreject_return_order(ret, admin=self.admin_user),
                    self.accept(ret),
                ),
            ),
        ):
            with self.subTest(case=label):
                prepare()
                with self.assertRaises(ValidationError) as caught:
                    revert_dispatch(order)
                self.assertIn(ret.public_id, " ".join(caught.exception.messages))
                order.refresh_from_db()
                self.assertEqual(order.status_id, StatusIds.DISPATCHED)

        revert_accept_return_order(ret, admin=self.admin_user)
        reject_return_order(ret, admin=self.admin_user)
        revert_dispatch(order)  # a rejected return does not hold the order
        order.refresh_from_db()
        self.assertEqual(order.status_id, StatusIds.CONFIRMED)

    def test_lots_booked_by_a_return_refuse_every_direct_change(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_lots_booked_by_a_return_refuse_every_direct_change"""
        order = self.dispatched_order()
        ret = self.new_return(order, 10)
        self.accept(ret, recipes=[self.recipe_p])
        raw_lot = InwardRawMaterial.objects.get(return_order=ret)
        other_lot = InwardOtherMaterial.objects.get(return_order=ret)
        mark = self.marker()

        attempts = {
            "edit the raw lot": lambda: InwardOperations.update_raw_lot(
                raw_lot, {"lab_sampling_date": TODAY}, self.su
            ),
            "delete the raw lot": lambda: raw_lot.mark_deleted(self.su),
            "delete the raw lot as the admin does": lambda: raw_lot.delete(deleted_by=self.su),
            "delete the other-material lot": lambda: other_lot.mark_deleted(self.su),
            "confirm the other-material lot": other_lot.refuse_return_lot_change,
        }
        for label, attempt in attempts.items():
            with self.subTest(case=label), self.assertRaises(ValidationError) as caught:
                attempt()
            self.assertIn(ret.public_id, " ".join(caught.exception.messages))

        self.assertTrue(InwardRawMaterial.objects.filter(return_order=ret).exists())
        self.assertTrue(InwardOtherMaterial.objects.filter(return_order=ret).exists())
        self.assertEqual(self.kinds_since(mark), [])

    def test_a_lot_needs_a_party_unless_a_return_booked_it(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_a_lot_needs_a_party_unless_a_return_booked_it"""
        ret = self.new_return(self.dispatched_order(), 10)
        bare = InwardRawMaterial(
            product=self.product,
            lot_no="X",
            quantity_kg=Decimal("1.000"),
            status_id=StatusIds.LAB_TESTING,
            created_by=self.su,
        )
        with self.assertRaises(ValidationError):
            bare.clean()
        bare.return_order = ret
        bare.clean()

    def test_only_a_pending_return_can_be_edited_and_lines_are_synced(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_only_a_pending_return_can_be_edited_and_lines_are_synced"""
        order = self.dispatched_order({self.pp1: 2, self.qq1: 3})
        ret = create_return_order(
            order,
            return_date=None,
            items=[self.item(self.product, 10), self.item(self.other_product, 5)],
            actor=self.sp_user,
        )

        update_return_order(
            ret,
            return_date=datetime.date(2026, 9, 1),
            items=[self.item(self.product, 20, price="7.50")],
            actor=self.admin_user,
        )
        ret.refresh_from_db()
        self.assertEqual(ret.return_date, datetime.date(2026, 9, 1))
        [line] = ret.items.all()
        self.assertEqual((line.packets, line.price_per_packet), (20, Decimal("7.50")))
        self.assertEqual(ReturnOrderItem.all_objects.filter(return_order=ret).count(), 2)

        # Putting the removed line back restores its row rather than adding one.
        update_return_order(
            ret,
            return_date=None,
            items=[self.item(self.product, 20), self.item(self.other_product, 6)],
            actor=self.admin_user,
        )
        self.assertEqual(ReturnOrderItem.all_objects.filter(return_order=ret).count(), 2)
        self.assertEqual(ret.items.count(), 2)

        with self.subTest(case="over the limit"):
            with self.assertRaises(ValidationError):
                update_return_order(
                    ret,
                    return_date=None,
                    items=[self.item(self.product, 41)],
                    actor=self.admin_user,
                )
            self.assertEqual(ret.items.count(), 2)

        with self.subTest(case="accepted"):
            self.accept(ret)
            with self.assertRaises(ValidationError):
                update_return_order(
                    ret, return_date=None, items=[self.item(self.product, 3)], actor=self.admin_user
                )
        with self.subTest(case="pending again after revert"):
            revert_accept_return_order(ret, admin=self.admin_user)
            update_return_order(
                ret, return_date=None, items=[self.item(self.product, 3)], actor=self.admin_user
            )
            self.assertEqual(ret.items.get().packets, 3)

        reject_return_order(ret, admin=self.admin_user)
        with self.assertRaises(ValidationError):
            update_return_order(
                ret, return_date=None, items=[self.item(self.product, 1)], actor=self.admin_user
            )

    def test_reject_and_unreject_only_apply_from_their_own_status_and_move_no_stock(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_reject_and_unreject_only_apply_from_their_own_status_and_move_no_stock"""
        order = self.dispatched_order()
        ret = self.new_return(order, 10)
        mark = self.marker()

        with self.assertRaises(ValidationError):
            unreject_return_order(ret, admin=self.admin_user)  # not rejected
        reject_return_order(ret, admin=self.admin_user)
        ret.refresh_from_db()
        self.assertEqual(ret.rejected_by_id, self.admin_user.pk)
        self.assertIsNotNone(ret.rejected_at)
        with self.assertRaises(ValidationError):
            reject_return_order(ret, admin=self.admin_user)  # already rejected
        unreject_return_order(ret, admin=self.admin_user)
        self.assertEqual(self.kinds_since(mark), [], "no stock moves, so no ledger row")

        self.accept(ret)
        with self.assertRaises(ValidationError):
            reject_return_order(ret, admin=self.admin_user)  # revert the accept first
        with self.assertRaises(ValidationError):
            self.accept(ret)  # already accepted
        with self.assertRaises(ValidationError):
            revert_accept_return_order(
                self.new_return(self.dispatched_order(), 1), admin=self.admin_user
            )  # a PENDING return has nothing to revert

    def test_only_a_sales_admin_can_accept_reject_or_revert(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_only_a_sales_admin_can_accept_reject_or_revert"""
        ret = self.new_return(self.dispatched_order(), 10)
        for label, action in (
            (
                "accept",
                lambda: accept_return_order(
                    ret, include_other=False, recipe_public_ids=None, admin=self.sp_user
                ),
            ),
            ("reject", lambda: reject_return_order(ret, admin=self.sp_user)),
            ("revert", lambda: revert_accept_return_order(ret, admin=self.sp_user)),
        ):
            with self.subTest(verb=label), self.assertRaises(PermissionDenied):
                action()

    def test_return_figures_in_the_payload(self):
        """tests/test_return_orders.py::ReturnOrderOperationsTest::test_return_figures_in_the_payload"""
        order = self.dispatched_order()
        ret = create_return_order(
            order,
            return_date=None,
            items=[self.item(self.product, 10, price="12.50")],
            actor=self.sp_user,
        )
        payload = return_order_payload(ret)
        self.assertEqual(payload["status"], "RETURN_PENDING")
        self.assertEqual(payload["total_kg"], "10.000")
        self.assertEqual(payload["total_amount"], "125.00")
        self.assertEqual(payload["order"]["public_id"], order.public_id)
        self.assertEqual(payload["inward_raw_materials"], [])
        self.accept(ret, recipes=[self.recipe_p])
        payload = return_order_payload(ret)
        self.assertEqual(len(payload["inward_raw_materials"]), 1)
        self.assertEqual(len(payload["inward_other_materials"]), 1)
        self.assertEqual(documented_keys_mismatches(ReturnOrderPayloadSerializer(), payload), [])


class ReturnOrderLedgerReportTest(ReturnWorldTestCase):
    """The accept and its revert show up in the product's ledger report."""

    def test_the_report_lists_the_return_event_with_its_source(self):
        """tests/test_return_orders.py::ReturnOrderLedgerReportTest::test_the_report_lists_the_return_event_with_its_source"""
        # Restart the ledger from the position setUp built, as go-live would.
        StockEventLine.objects.all().delete()
        StockEvent.objects.all().delete()
        StockLedgerOperations.seed_ledger()

        order = self.dispatched_order()
        ret = self.new_return(order, 10)
        self.accept(ret, recipes=[self.recipe_p])
        revert_accept_return_order(ret, admin=self.admin_user)

        rows = product_ledger_rows(self.product, TODAY, TODAY)
        events = [row for row in rows if row["event"] == "RETURN_OPERATIONS"]
        self.assertEqual(
            [row["detail"] for row in events], ["RETURN_ACCEPTED", "RETURN_ACCEPT_REVERTED"]
        )
        for row in events:
            self.assertEqual(
                row["source"],
                {
                    "kind": "return_order",
                    "public_id": ret.public_id,
                    "label": self.client_obj.company_name,
                },
            )
            self.assertEqual(row["actor"]["id"], self.admin_user.pk)
        self.assertEqual(events[0]["raw_material"]["change"]["incoming"], "10.000")
        self.assertEqual(events[1]["raw_material"]["change"]["incoming"], "-10.000")


class ReturnOrderApiTest(ReturnWorldTestCase):
    """The Android and sales-admin endpoints.

    tests/test_return_orders.py::ReturnOrderApiTest
    """

    ANDROID = "/android/api/v1/"
    ADMIN = "/api/sales-admin/"

    def setUp(self):
        super().setUp()
        self.web = APIClient()
        self.web.force_login(self.admin_user)
        self.droid = self.android_client(self.sp_user)

    @staticmethod
    def android_client(user) -> APIClient:
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    def body(self, packets=15, price="90.50", **extra):
        return {
            "items": [
                {
                    "product_public_id": self.product.public_id,
                    "packet_weight": "1.000",
                    "packets": packets,
                    "price_per_packet": price,
                }
            ],
            **extra,
        }

    def raise_return(self, order, packets=15, **kwargs):
        response = self.droid.post(
            f"{self.ANDROID}return-order/{order.public_id}",
            self.body(packets, **kwargs),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        return ReturnOrder.objects.get(public_id=response.data["public_id"])

    # -- Android -----------------------------------------------------------------

    def test_android_prefill_then_create(self):
        """tests/test_return_orders.py::ReturnOrderApiTest::test_android_prefill_then_create"""
        order = self.dispatched_order()
        url = f"{self.ANDROID}return-order/{order.public_id}"

        prefill = self.droid.get(url)
        self.assertEqual(prefill.status_code, status.HTTP_200_OK, prefill.content)
        self.assertEqual(
            documented_keys_mismatches(ReturnOrderPrefillSerializer(), prefill.data), []
        )
        [line] = prefill.data["lines"]
        suggested = (self.pp1.selling_price / 20).quantize(Decimal("0.01"))
        self.assertEqual(line["product"]["public_id"], self.product.public_id)
        self.assertEqual(line["packet_weight"], "1.000")
        self.assertEqual(line["dispatched_packets"], 40)
        self.assertEqual(line["returnable_packets"], 40)
        self.assertEqual(Decimal(line["suggested_price_per_packet"]), suggested)
        self.assertIsNone(prefill.data["return_order"])
        self.assertEqual(prefill.data["order"]["status"], "DISPATCHED")

        bad = [
            ("over the limit", self.body(41)),
            ("negative price", self.body(price="-1.00")),
            ("zero packets", self.body(0)),
            ("no items", {"items": []}),
            ("missing items", {}),
            (
                "unknown product",
                {"items": [{**self.body()["items"][0], "product_public_id": "P-NOSUCHPRODUCT"}]},
            ),
        ]
        for label, payload in bad:
            with self.subTest(case=label):
                response = self.droid.post(url, payload, format="json")
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.content
                )
        self.assertFalse(ReturnOrder.objects.exists())

        created = self.droid.post(url, self.body(15, return_date="2026-10-01"), format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        self.assertEqual(
            documented_keys_mismatches(ReturnOrderPayloadSerializer(), created.data), []
        )
        self.assertEqual(created.data["status"], "RETURN_PENDING")
        self.assertEqual(created.data["return_date"], "2026-10-01")
        self.assertEqual(created.data["total_kg"], "15.000")
        self.assertEqual(created.data["total_amount"], "1357.50")
        self.assertEqual(created.data["created_by"]["id"], self.sp_user.pk)

        again = self.droid.get(url)
        self.assertEqual(again.data["lines"][0]["returnable_packets"], 25)
        self.assertEqual(again.data["return_order"]["public_id"], created.data["public_id"])
        self.assertEqual(
            self.droid.post(url, self.body(5), format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
            "only one live return per order",
        )

    def test_android_sales_people_only_reach_their_own_orders_and_dispatched_ones(self):
        """tests/test_return_orders.py::ReturnOrderApiTest::test_android_sales_people_only_reach_their_own_orders_and_dispatched_ones"""
        order = self.dispatched_order()
        stranger = self.android_client(self.other_sp)
        url = f"{self.ANDROID}return-order/{order.public_id}"
        self.assertEqual(stranger.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            stranger.post(url, self.body(), format="json").status_code, status.HTTP_404_NOT_FOUND
        )

        confirmed = self.order(self.pp1, 2)
        response = self.droid.post(
            f"{self.ANDROID}return-order/{confirmed.public_id}", self.body(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            self.droid.get(f"{self.ANDROID}return-order/{confirmed.public_id}").data["lines"], []
        )
        self.assertFalse(ReturnOrder.objects.exists())

    def test_android_get_return_orders_lists_only_the_callers_returns(self):
        """tests/test_return_orders.py::ReturnOrderApiTest::test_android_get_return_orders_lists_only_the_callers_returns"""
        mine = self.raise_return(self.dispatched_order(), 5)
        theirs_order = self.dispatched_order(actor=self.other_sp)
        stranger = self.android_client(self.other_sp)
        stranger.post(
            f"{self.ANDROID}return-order/{theirs_order.public_id}", self.body(3), format="json"
        )
        reject_return_order(ReturnOrder.objects.get(order=theirs_order), admin=self.admin_user)

        listed = self.droid.get(f"{self.ANDROID}get-return-orders")
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.content)
        self.assertEqual([r["public_id"] for r in listed.data["results"]], [mine.public_id])
        for result in listed.data["results"]:
            self.assertEqual(
                documented_keys_mismatches(ReturnOrderListItemSerializer(), result), []
            )

        self.assertEqual(
            self.droid.get(f"{self.ANDROID}get-return-orders", {"status": "RETURN_REJECTED"}).data[
                "total_count"
            ],
            0,
        )
        self.assertEqual(
            self.droid.get(
                f"{self.ANDROID}get-return-orders", {"order": mine.order.public_id}
            ).data["total_count"],
            1,
        )

    # -- sales admin ---------------------------------------------------------------

    def test_admin_lists_filters_and_sorts_returns(self):
        """tests/test_return_orders.py::ReturnOrderApiTest::test_admin_lists_filters_and_sorts_returns"""
        small = self.raise_return(self.dispatched_order(), 2, price="1.00")
        order_q = self.dispatched_order({self.qq1: 3})
        big = create_return_order(
            order_q,
            return_date=None,
            items=[self.item(self.other_product, 20, price="9.00")],
            actor=self.sp_user,
        )
        reject_return_order(big, admin=self.admin_user)
        url = f"{self.ADMIN}return-orders/"

        everything = self.web.get(url)
        self.assertEqual(everything.status_code, status.HTTP_200_OK, everything.content)
        self.assertEqual(everything.data["total_count"], 2)
        for result in everything.data["results"]:
            self.assertEqual(
                documented_keys_mismatches(ReturnOrderListItemSerializer(), result), []
            )

        def ids(**params):
            response = self.web.get(url, params)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
            return [r["public_id"] for r in response.data["results"]]

        filters = {
            "status": ({"status": "RETURN_REJECTED"}, [big.public_id]),
            "public id": ({"public_id": small.public_id[-6:]}, [small.public_id]),
            "sales person": ({"created_by": self.sp_user.pk}, [big.public_id, small.public_id]),
            "client": ({"client": self.client_obj.pk}, [big.public_id, small.public_id]),
            "product": ({"product": self.other_product.pk}, [big.public_id]),
            "order": ({"order": order_q.public_id}, [big.public_id]),
        }
        for label, (params, expected) in filters.items():
            with self.subTest(filter=label):
                self.assertCountEqual(ids(**params), expected)

        with self.subTest(sort="value"):
            self.assertEqual(ids(sort="value"), [small.public_id, big.public_id])
            self.assertEqual(ids(sort="-value"), [big.public_id, small.public_id])
        with self.subTest(sort="created_at"):
            self.assertEqual(ids(sort="created_at"), [small.public_id, big.public_id])
        with self.subTest(case="unknown status"):
            self.assertEqual(
                self.web.get(url, {"status": "NOPE"}).status_code, status.HTTP_400_BAD_REQUEST
            )

    def test_admin_accepts_with_recipes_and_the_stock_screens_follow(self):
        """tests/test_return_orders.py::ReturnOrderApiTest::test_admin_accepts_with_recipes_and_the_stock_screens_follow"""
        order = self.dispatched_order()
        ret = self.raise_return(order, 15)
        old = self.recipe_p
        live = self.replace_recipe_p("3.000")

        picker = self.web.get(f"{self.ADMIN}return-order-recipes/{ret.public_id}")
        self.assertEqual(picker.status_code, status.HTTP_200_OK, picker.content)
        self.assertEqual(
            documented_keys_mismatches(ReturnOrderRecipesSerializer(), picker.data), []
        )
        [line] = picker.data["lines"]
        self.assertEqual(
            {r["public_id"]: r["is_deleted"] for r in line["recipes"]},
            {old.public_id: True, live.public_id: False},
        )

        def stock():
            raw = self.web.get(f"{self.ADMIN}raw-material-stock").data["lines"]
            other = self.web.get(f"{self.ADMIN}other-material-stock").data["lines"]
            return (
                Decimal(
                    next(r for r in raw if r["product"] == self.product.public_id)["incoming_kg"]
                ),
                Decimal(
                    next(m for m in other if m["material_type"]["id"] == self.pouch.id)["on_hand"]
                ),
            )

        raw_before, pouches_before = stock()
        accept_url = f"{self.ADMIN}accept-return-order/{ret.public_id}"

        for label, payload in (
            ("flag missing", {}),
            (
                "recipes without the flag",
                {"include_in_other_raw_materials": False, "recipe_public_ids": [live.public_id]},
            ),
            ("flag without recipes", {"include_in_other_raw_materials": True}),
        ):
            with self.subTest(case=label):
                response = self.web.post(accept_url, payload, format="json")
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.content
                )
        self.assertEqual(stock(), (raw_before, pouches_before))

        accepted = self.web.post(
            accept_url,
            {"include_in_other_raw_materials": True, "recipe_public_ids": [live.public_id]},
            format="json",
        )
        self.assertEqual(accepted.status_code, status.HTTP_200_OK, accepted.content)
        self.assertEqual(
            documented_keys_mismatches(ReturnOrderPayloadSerializer(), accepted.data), []
        )
        self.assertEqual(accepted.data["status"], "RETURN_ACCEPTED")
        self.assertIs(accepted.data["include_in_other_raw_materials"], True)
        self.assertEqual(accepted.data["verified_by"]["id"], self.admin_user.pk)
        self.assertEqual(len(accepted.data["inward_raw_materials"]), 1)
        self.assertEqual(len(accepted.data["inward_other_materials"]), 1)

        # Raw incoming and pouch on-hand both went up: 15 kg, and 15 packets x 3.
        raw_after, pouches_after = stock()
        self.assertEqual(raw_after - raw_before, Decimal("15"))
        self.assertEqual(pouches_after - pouches_before, Decimal("45"))

        # The lots read back through the normal inward lists, with no party.
        raw_lots = self.web.get(f"{self.ADMIN}inward-raw-materials", {"public_id": "IR-"}).data[
            "results"
        ]
        [returned] = [lot for lot in raw_lots if lot["return_order"]]
        self.assertIsNone(returned["party"]["id"])
        self.assertEqual(returned["party"]["name"], f"Return Order ({order.public_id})")
        self.assertEqual(returned["return_order"]["public_id"], ret.public_id)
        self.assertEqual(returned["lot_no"], ret.public_id)
        other_lots = self.web.get(f"{self.ADMIN}inward-other-materials").data["results"]
        [returned_other] = [lot for lot in other_lots if lot["return_order"]]
        self.assertIsNone(returned_other["party"]["id"])

        # ... and are refused every direct change.
        raw_url = f"{self.ADMIN}inward-raw-material/{returned['public_id']}"
        other_url = f"{self.ADMIN}inward-other-material/{returned_other['public_id']}"
        refusals = {
            "patch raw": self.web.patch(
                raw_url, {"lab_sampling_date": "2026-10-03"}, format="json"
            ),
            "delete raw": self.web.delete(raw_url),
            "patch other": self.web.patch(other_url, {}, format="json"),
            "delete other": self.web.delete(other_url),
        }
        for label, response in refusals.items():
            with self.subTest(case=label):
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.content
                )
        self.assertTrue(InwardRawMaterial.objects.filter(return_order=ret).exists())

        exported = self.web.get(
            f"{self.ADMIN}export/inward-entries",
            {"start_date": TODAY.isoformat(), "end_date": TODAY.isoformat()},
        )
        self.assertEqual(exported.status_code, status.HTTP_200_OK, exported.content)
        self.assertEqual(
            documented_keys_mismatches(ExportInwardEntriesResponseSerializer(), exported.data), []
        )
        [day] = exported.data["results"]
        self.assertTrue(any(lot["return_order"] for lot in day["raw_materials"]))
        self.assertTrue(any(lot["return_order"] for lot in day["other_materials"]))

        # Reverting removes them, and the figures go back.
        reverted = self.web.post(f"{self.ADMIN}revert-accept-return-order/{ret.public_id}")
        self.assertEqual(reverted.status_code, status.HTTP_200_OK, reverted.content)
        self.assertEqual(reverted.data["status"], "RETURN_PENDING")
        self.assertEqual(reverted.data["inward_raw_materials"], [])
        self.assertEqual(stock(), (raw_before, pouches_before))

    def test_admin_lifecycle_endpoints_and_the_order_detail(self):
        """tests/test_return_orders.py::ReturnOrderApiTest::test_admin_lifecycle_endpoints_and_the_order_detail"""
        order = self.dispatched_order()
        ret = self.raise_return(order, 10)
        detail_url = f"{self.ADMIN}order/{order.public_id}"
        verb = lambda name: f"{self.ADMIN}{name}/{ret.public_id}"  # noqa: E731

        detail = self.web.get(detail_url)
        self.assertEqual(detail.data["return_order"]["public_id"], ret.public_id)
        self.assertEqual(
            documented_keys_mismatches(ReturnOrderPayloadSerializer(), detail.data["return_order"]),
            [],
        )

        edited = self.web.patch(
            verb("edit-return-order"), self.body(20, price="2.00"), format="json"
        )
        self.assertEqual(edited.status_code, status.HTTP_200_OK, edited.content)
        self.assertEqual(edited.data["total_kg"], "20.000")
        self.assertEqual(
            self.web.patch(verb("edit-return-order"), self.body(41), format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # revert-dispatch is blocked while the return is live.
        blocked = self.web.post(f"{self.ADMIN}revert-dispatch/{order.public_id}")
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST, blocked.content)

        rejected = self.web.post(verb("reject-return-order"))
        self.assertEqual(rejected.status_code, status.HTTP_200_OK, rejected.content)
        self.assertEqual(rejected.data["status"], "RETURN_REJECTED")
        self.assertEqual(rejected.data["rejected_by"]["id"], self.admin_user.pk)
        # A rejected return is hidden from the order's details.
        self.assertIsNone(self.web.get(detail_url).data["return_order"])
        self.assertEqual(
            self.web.patch(verb("edit-return-order"), self.body(5), format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
            "only a pending return is editable",
        )
        self.assertEqual(
            self.web.post(verb("reject-return-order")).status_code, status.HTTP_400_BAD_REQUEST
        )

        unrejected = self.web.post(verb("unreject-return-order"))
        self.assertEqual(unrejected.status_code, status.HTTP_200_OK, unrejected.content)
        self.assertEqual(unrejected.data["status"], "RETURN_PENDING")
        self.assertEqual(self.web.get(detail_url).data["return_order"]["public_id"], ret.public_id)

        # Unknown returns are 404s for every verb.
        for name in (
            "accept-return-order",
            "reject-return-order",
            "unreject-return-order",
            "revert-accept-return-order",
        ):
            with self.subTest(verb=name):
                self.assertEqual(
                    self.web.post(
                        f"{self.ADMIN}{name}/RET-NOSUCHRETURN",
                        {"include_in_other_raw_materials": False},
                        format="json",
                    ).status_code,
                    status.HTTP_404_NOT_FOUND,
                )
        self.assertEqual(
            self.web.get(f"{self.ADMIN}return-order-recipes/RET-NOSUCHRETURN").status_code,
            status.HTTP_404_NOT_FOUND,
        )


class ReturnOrderFreezeTest(ReturnWorldTestCase):
    """A frozen product (``is_usable = False``) takes no new return stock movement.

    tests/test_return_orders.py::ReturnOrderFreezeTest
    """

    def freeze(self, product):
        Product.objects.filter(pk=product.pk).update(is_usable=False)
        product.refresh_from_db()

    def test_a_return_cannot_be_raised_for_a_frozen_product(self):
        """tests/test_return_orders.py::ReturnOrderFreezeTest::test_a_return_cannot_be_raised_for_a_frozen_product"""
        order = self.dispatched_order()
        self.freeze(self.product)
        with self.assertRaises(ValidationError) as ctx:
            self.new_return(order)
        self.assertIn("not usable", str(ctx.exception))
        self.assertFalse(ReturnOrder.all_objects.exists())

    def test_a_pending_return_can_shrink_but_not_grow_or_be_accepted_while_frozen(self):
        """Releases stay open: lowering and rejecting work; raising and accepting do not.

        tests/test_return_orders.py::ReturnOrderFreezeTest::test_a_pending_return_can_shrink_but_not_grow_or_be_accepted_while_frozen
        """
        order = self.dispatched_order()
        ret = self.new_return(order, 10)
        self.freeze(self.product)

        with self.assertRaises(ValidationError):
            update_return_order(
                ret, return_date=None, items=[self.item(self.product, 20)], actor=self.sp_user
            )
        update_return_order(
            ret, return_date=None, items=[self.item(self.product, 5)], actor=self.sp_user
        )
        self.assertEqual(ret.items.get().packets, 5)

        raw_before = InwardRawMaterial.objects.count()
        with self.assertRaises(ValidationError) as ctx:
            self.accept(ret)
        self.assertIn("not usable", str(ctx.exception))
        self.assertEqual(InwardRawMaterial.objects.count(), raw_before)

        reject_return_order(ret, admin=self.admin_user)
        ret.refresh_from_db()
        self.assertEqual(ret.status_id, StatusIds.RETURN_REJECTED)

    def test_an_accepted_return_cannot_be_reverted_while_its_product_is_frozen(self):
        """Its inward lots are existing rows, so they are read-only until unfrozen.

        tests/test_return_orders.py::ReturnOrderFreezeTest::test_an_accepted_return_cannot_be_reverted_while_its_product_is_frozen
        """
        ret = self.new_return(self.dispatched_order(), 10)
        self.accept(ret)
        self.freeze(self.product)

        with self.assertRaises(ValidationError):
            revert_accept_return_order(ret, admin=self.admin_user)
        self.assertTrue(InwardRawMaterial.objects.filter(return_order=ret).exists())

        Product.objects.filter(pk=self.product.pk).update(is_usable=True)
        revert_accept_return_order(ret, admin=self.admin_user)
        self.assertFalse(InwardRawMaterial.objects.filter(return_order=ret).exists())
