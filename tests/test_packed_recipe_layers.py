"""Packed-recipe layers: packing material is frozen at the recipe in force when packed.

Each count row carries layers -- how many of its packed packets were packed
under which recipe. A recipe change (delete + create) therefore never re-values
packets that are already packed, and unpacking takes the newest layers first.

Run: bash scripts/run.sh test-serial tests/test_packed_recipe_layers.py
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from aggregator import InventoryOperations as inv
from aggregator.models import InventorySnapshot, OtherMaterialRecipe, PackedRecipeLayer
from tests.stock_ledger_support import TODAY, W1, LedgerWorldTestCase

TOMORROW = TODAY + datetime.timedelta(days=1)


class PackedRecipeLayersTest(LedgerWorldTestCase):
    def setUp(self):
        super().setUp()
        self.raw(self.product, "100000")
        self.pouches("100000")
        self.count_everything({self.pp1: 0})

    def _layers(self, day=None):
        row = InventorySnapshot.objects.get(
            product_packaging=self.pp1, snapshot_date=day or inv.latest_snapshot_date()
        )
        return [
            (layer.recipe_id, layer.packets)
            for layer in PackedRecipeLayer.objects.filter(inventory_snapshot=row).order_by(
                "opened_at", "id"
            )
        ]

    def _used(self):
        return inv.other_material_used([self.pouch.pk]).get(self.pouch.pk, Decimal("0"))

    def _replace_recipe(self, quantity):
        self.recipe_p.mark_deleted(self.su)
        self.recipe_p = OtherMaterialRecipe.objects.create(
            product=self.product, material_type=self.pouch, packet_weight=W1,
            quantity=Decimal(quantity), created_by=self.su,
        )

    def test_packing_layers_the_new_packets_at_the_live_recipe(self):
        """tests/test_packed_recipe_layers.py::PackedRecipeLayersTest::test_packing_layers_the_new_packets_at_the_live_recipe"""
        self.count_bags({self.pp1: 5})  # 100 packets
        self.assertEqual(self._layers(), [(self.recipe_p.pk, 100)])
        self.count_bags({self.pp1: 6})  # +20, same recipe: the layer grows
        self.assertEqual(self._layers(), [(self.recipe_p.pk, 120)])
        self.assertEqual(self._used(), Decimal("120"))

    def test_a_recipe_change_does_not_revalue_what_is_already_packed(self):
        """tests/test_packed_recipe_layers.py::PackedRecipeLayersTest::test_a_recipe_change_does_not_revalue_what_is_already_packed"""
        self.count_bags({self.pp1: 5})  # 100 packets at 1 a packet
        old = self.recipe_p.pk
        self._replace_recipe("2.000")
        self.assertEqual(self._used(), Decimal("100"), "history is frozen")
        self.count_bags({self.pp1: 7})  # +40 packets at 2 a packet
        self.assertEqual(self._layers(), [(old, 100), (self.recipe_p.pk, 40)])
        self.assertEqual(self._used(), Decimal("180"))  # 100 x 1 + 40 x 2

    def test_unpacking_takes_the_newest_layers_first_across_layers(self):
        """tests/test_packed_recipe_layers.py::PackedRecipeLayersTest::test_unpacking_takes_the_newest_layers_first_across_layers"""
        self.count_bags({self.pp1: 5})
        old = self.recipe_p.pk
        self._replace_recipe("2.000")
        self.count_bags({self.pp1: 7})  # layers: old 100, new 40
        self.count_bags({self.pp1: 4})  # -60 packets: new 40 goes, then old -20
        self.assertEqual(self._layers(), [(old, 80)])
        self.assertEqual(self._used(), Decimal("80"))

    def test_packets_packed_while_no_recipe_existed_spend_nothing(self):
        """tests/test_packed_recipe_layers.py::PackedRecipeLayersTest::test_packets_packed_while_no_recipe_existed_spend_nothing"""
        self.count_bags({self.pp1: 5})
        old = self.recipe_p.pk
        self.recipe_p.mark_deleted(self.su)  # no replacement
        self.count_bags({self.pp1: 6})
        self.assertEqual(self._layers(), [(old, 100), (None, 20)])
        self.assertEqual(self._used(), Decimal("100"))
        self.count_bags({self.pp1: 5})  # unpack the NULL layer first
        self.assertEqual(self._layers(), [(old, 100)])

    def test_a_new_day_copies_the_layers_and_counts_stack_on_them(self):
        """tests/test_packed_recipe_layers.py::PackedRecipeLayersTest::test_a_new_day_copies_the_layers_and_counts_stack_on_them"""
        self.count_bags({self.pp1: 5})
        today_layers = self._layers()
        self.count_bags({self.pp1: 6}, day=TOMORROW)
        self.assertEqual(self._layers(TODAY), today_layers, "yesterday's row is untouched")
        self.assertEqual(self._layers(TOMORROW), [(self.recipe_p.pk, 120)])
        self.assertEqual(self._used(), Decimal("120"), "only the latest row is read")

    def test_deleting_the_latest_count_falls_back_to_the_previous_rows_layers(self):
        """tests/test_packed_recipe_layers.py::PackedRecipeLayersTest::test_deleting_the_latest_count_falls_back_to_the_previous_rows_layers"""
        self.count_bags({self.pp1: 5})
        self.count_bags({self.pp1: 8}, day=TOMORROW)
        self.assertEqual(self._used(), Decimal("160"))
        InventorySnapshot.objects.get(
            product_packaging=self.pp1, snapshot_date=TOMORROW
        ).mark_deleted(self.su)
        self.assertEqual(self._used(), Decimal("100"))

    def test_layered_packets_never_exceed_packed_packets(self):
        """tests/test_packed_recipe_layers.py::PackedRecipeLayersTest::test_layered_packets_never_exceed_packed_packets"""
        for bags in (5, 9, 3, 0, 6, 2):
            with self.subTest(bags=bags):
                self.count_bags({self.pp1: bags})
                layered = sum(packets for _, packets in self._layers())
                self.assertLessEqual(layered, bags * 20)
                self.assertEqual(self._used(), Decimal(layered))

    def test_another_products_recipe_charges_the_same_material_separately(self):
        """tests/test_packed_recipe_layers.py::PackedRecipeLayersTest::test_another_products_recipe_charges_the_same_material_separately"""
        self.raw(self.other_product, "100000")
        self.count_everything({self.pp1: 5, self.qq1: 3})  # 100 P packets, 30 Q packets
        # P spends 1 a packet, Q 2 a packet: 100 + 60.
        self.assertEqual(self._used(), Decimal("160"))
        self.assertEqual(
            inv.other_material_used([self.pouch.pk], product=self.other_product),
            {self.pouch.pk: Decimal("60")},
        )
