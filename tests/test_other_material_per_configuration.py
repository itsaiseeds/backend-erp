"""Packing material is stocked per configuration ``(product, packet weight, type)``.

See docs/prd/other-material-per-configuration-stock.md.

Run: bash scripts/run.sh test-serial tests/test_other_material_per_configuration.py
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations, StockLedgerOperations
from aggregator.models import (
    InventorySnapshot,
    OtherMaterialRecipe,
    StockEvent,
    StockEventLine,
    StockPoolKind,
)
from aggregator.ProductOperations import add_packaging
from tests.stock_ledger_support import W1, LedgerWorldTestCase

W3 = Decimal("3.000")


class OtherMaterialPerConfigurationTest(LedgerWorldTestCase):
    def setUp(self):
        super().setUp()
        self.raw(self.product, "100000")
        self.raw(self.other_product, "100000")

    def _seed(self):
        """Go live from a clean slate (setUp's bookings already wrote events)."""
        StockEventLine.objects.all().delete()
        StockEvent.objects.all().delete()
        StockLedgerOperations.seed_ledger()

    def _material_error(self, counts):
        with self.assertRaises(ValueError) as caught:
            self.count_everything(counts)
        return str(caught.exception)

    def test_p_inward_cannot_back_q_packets(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_p_inward_cannot_back_q_packets"""
        self.pouches("1000", recipe=self.recipe_p)
        message = self._material_error({self.qq1: 1})
        self.assertIn("'Ledger Q' 1.000kg", message)
        self.assertFalse(InventorySnapshot.objects.filter(product_packaging=self.qq1).exists())

    def test_p_inward_cannot_back_p_packets_of_another_weight(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_p_inward_cannot_back_p_packets_of_another_weight"""
        pp3 = add_packaging(self.product, packet_weight=W3, packets=4, actor=self.su)
        OtherMaterialRecipe.objects.create(
            product=self.product,
            material_type=self.pouch,
            packet_weight=W3,
            quantity=Decimal("1.000"),
            created_by=self.su,
        )
        self.pouches("1000", recipe=self.recipe_p)
        self.assertIn("'Ledger P' 3.000kg", self._material_error({pp3: 1}))

    def test_stock_booked_under_an_old_recipe_version_still_counts(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_stock_booked_under_an_old_recipe_version_still_counts"""
        self.pouches("100", recipe=self.recipe_p)
        self.recipe_p.mark_deleted(self.su)
        OtherMaterialRecipe.objects.create(
            product=self.product,
            material_type=self.pouch,
            packet_weight=W1,
            quantity=Decimal("3.000"),
            created_by=self.su,
        )
        self.count_everything({self.pp1: 1})  # 20 packets x 3 = 60 <= 100
        key = (self.product.pk, W1, self.pouch.pk)
        self.assertEqual(inv.other_material_available([key])[key], Decimal("40"))

    def test_recipe_changes_never_move_packed_stock(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_recipe_changes_never_move_packed_stock"""
        self.pouches("1000", recipe=self.recipe_p)
        self.count_everything({self.pp1: 5})  # 100 packets at 1
        key = (self.product.pk, W1, self.pouch.pk)
        self.assertEqual(inv.other_material_available([key])[key], Decimal("900"))
        self.recipe_p.mark_deleted(self.su)  # frees nothing
        self.assertEqual(inv.other_material_available([key])[key], Decimal("900"))
        OtherMaterialRecipe.objects.create(
            product=self.product,
            material_type=self.pouch,
            packet_weight=W1,
            quantity=Decimal("5.000"),
            created_by=self.su,
        )  # re-values nothing
        self.assertEqual(inv.other_material_available([key])[key], Decimal("900"))
        self.assertEqual(inv.available_bags(self.pp1), 5)

    def test_deleting_a_lot_is_judged_on_its_own_configuration(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_deleting_a_lot_is_judged_on_its_own_configuration"""
        lot_p = self.pouches("500", recipe=self.recipe_p)
        lot_q = self.pouches("1000", recipe=self.recipe_q)
        self.count_everything({self.pp1: 5})
        lot_q.mark_deleted(self.su)  # only Q's stock goes; Q uses none, so it is allowed
        with self.assertRaises(ValidationError):
            lot_p.mark_deleted(self.su)  # P's 100 packets would be left uncovered
        self.assertTrue(lot_q.is_deleted)

    def test_deleting_the_lot_p_packets_use_is_refused(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_deleting_the_lot_p_packets_use_is_refused"""
        lot_p = self.pouches("100", recipe=self.recipe_p)
        self.count_everything({self.pp1: 5})  # uses all 100
        with self.assertRaises(ValidationError) as caught:
            lot_p.mark_deleted(self.su)
        self.assertIn("'Ledger P' 1.000kg", str(caught.exception))

    def test_screens_sum_the_configurations_per_type(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_screens_sum_the_configurations_per_type"""
        self.pouches("1000")
        self.count_everything({self.pp1: 5, self.qq1: 3})
        flat = {
            line["material_type_id"]: line["on_hand"]
            for line in InwardOperations.other_material_on_hand()
        }
        summed: dict[int, Decimal] = {}
        for line in InwardOperations.other_material_on_hand_by_configuration():
            summed[line["material_type_id"]] = (
                summed.get(line["material_type_id"], Decimal("0")) + line["on_hand"]
            )
        self.assertEqual(flat[self.pouch.pk], summed[self.pouch.pk])
        self.assertEqual(flat[self.pouch.pk], Decimal("2000") - 100 - 60)

    def test_ledger_pools_reconcile_per_configuration(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_ledger_pools_reconcile_per_configuration"""
        self._seed()
        self.pouches("1000")
        self.count_everything({self.pp1: 5, self.qq1: 3})
        self.assertEqual(StockLedgerOperations.check_ledger(), [])
        lines = StockEventLine.objects.filter(
            pool_kind=StockPoolKind.OTHER, event__product=self.product
        )
        self.assertEqual({line.packet_weight for line in lines}, {W1})
        self.assertEqual(sum(line.d_incoming or 0 for line in lines), Decimal("1000"))

    def test_rebuild_repairs_the_other_lines_and_is_idempotent(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_rebuild_repairs_the_other_lines_and_is_idempotent"""
        self.pouches("1000")
        self.count_everything({self.pp1: 5})
        self._seed()
        self.assertEqual(StockLedgerOperations.rebuild_other_material_ledger(), 0)
        StockEventLine.objects.filter(pool_kind=StockPoolKind.OTHER).delete()
        self.assertNotEqual(StockLedgerOperations.check_ledger(), [])
        self.assertGreater(StockLedgerOperations.rebuild_other_material_ledger(), 0)
        self.assertEqual(StockLedgerOperations.check_ledger(), [])
        self.assertEqual(StockLedgerOperations.rebuild_other_material_ledger(), 0)

    def test_rebuild_does_nothing_on_an_unseeded_ledger(self):
        """tests/test_other_material_per_configuration.py::OtherMaterialPerConfigurationTest::test_rebuild_does_nothing_on_an_unseeded_ledger"""
        self.assertEqual(StockLedgerOperations.rebuild_other_material_ledger(), 0)
