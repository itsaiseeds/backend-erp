"""``reuse_other_material`` on the bag and loose count writers.

With it ``false`` what comes off a lowered line is discarded (a raised line
ignores the flag, and never offsets a lowered one): the seed returns to raw,
but the packing material (leaflets, covers) used on those packets is not given
back -- it is written off the inward lots, so the available material does not
go up. No column records it. These tests drive the
real writers and read the figures the stock screens read; the ledger drift guard
of ``DMLTestCase`` also runs after each one.

Run: bash scripts/run.sh test-serial tests/test_reuse_other_material.py
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from aggregator import InventoryOperations as inv
from aggregator.models import InwardOtherMaterial
from aggregator.ProductOperations import add_packaging
from authentication.models import Admin
from tests.stock_ledger_support import TODAY, W1, LedgerWorldTestCase

User = get_user_model()

TOMORROW = TODAY + datetime.timedelta(days=1)
BAG_URL = "/api/sales-admin/update-bag-stock"
LOOSE_URL = "/api/sales-admin/update-sample-packet-stock"


class _AvailableLeaflets:
    def _available(self):
        """Leaflets left for the product's 1 kg packets (one leaflet a packet)."""
        key = (self.product.pk, W1, self.pouch.pk)
        return inv.other_material_available([key])[key]

    def _booked(self):
        """Leaflets on the product's live inward lots."""
        lots = InwardOtherMaterial.objects.filter(recipe=self.recipe_p)
        return sum((lot.quantity for lot in lots), Decimal("0"))


class ReuseOtherMaterialTest(_AvailableLeaflets, LedgerWorldTestCase):
    """tests/test_reuse_other_material.py::ReuseOtherMaterialTest"""

    def setUp(self):
        super().setUp()
        self.raw(self.product, "100000")
        self.raw(self.other_product, "100000")
        self.pouches("100000")
        # A complete count: orders can only be verified against a full one.
        self.count_everything({self.pp1: 0, self.qq1: 0})

    # -- bags -------------------------------------------------------------------

    def test_lowering_with_reuse_gives_the_material_back(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_lowering_with_reuse_gives_the_material_back"""
        self.count_bags({self.pp1: 5})  # 100 packets, 100 leaflets
        self.count_bags({self.pp1: 2})

        self.assertEqual(self._available(), Decimal("99960"), "60 leaflets came back")
        self.assertEqual(self._booked(), Decimal("100000"), "the lots are untouched")

    def test_lowering_without_reuse_discards_the_material_but_returns_the_seed(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_lowering_without_reuse_discards_the_material_but_returns_the_seed"""
        self.count_bags({self.pp1: 5})
        raw_before = inv.raw_available_kg(self.product)

        self.count_bags({self.pp1: 2}, reuse_other_material=False)  # 60 packets off

        self.assertEqual(self._available(), Decimal("99900"), "the leaflets are not given back")
        self.assertEqual(self._booked(), Decimal("99940"), "they are written off the lot")
        self.assertEqual(inv.raw_available_kg(self.product), raw_before + 60, "the seed is")
        self.assertEqual(inv.on_hand_bags(self.pp1, inv.latest_snapshot_date()), 2)

    def test_a_discard_can_be_repeated(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_a_discard_can_be_repeated"""
        self.count_bags({self.pp1: 5})
        self.count_bags({self.pp1: 2}, reuse_other_material=False)
        self.count_bags({self.pp1: 1}, reuse_other_material=False)
        self.count_bags({self.pp1: 0}, reuse_other_material=False)

        self.assertEqual(self._available(), Decimal("99900"))
        self.assertEqual(self._booked(), Decimal("99900"))

    def test_a_new_day_keeps_the_discard(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_a_new_day_keeps_the_discard"""
        self.count_bags({self.pp1: 5})
        self.count_bags({self.pp1: 2}, reuse_other_material=False)

        self.count_bags({self.pp1: 3}, day=TOMORROW)  # reuse allowed: +20 packets

        self.assertEqual(self._available(), Decimal("99880"))

    def test_without_reuse_a_raise_ignores_the_flag(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_without_reuse_a_raise_ignores_the_flag"""
        self.count_bags({self.pp1: 5})

        self.count_bags({self.pp1: 6}, reuse_other_material=False)  # +20 packets, as usual
        self.assertEqual(inv.on_hand_bags(self.pp1, inv.latest_snapshot_date()), 6)
        self.assertEqual(self._available(), Decimal("99880"))
        self.assertEqual(self._booked(), Decimal("100000"), "nothing written off")

        self.count_bags({self.pp1: 6}, reuse_other_material=False)  # the same is no raise
        self.assertEqual(self._booked(), Decimal("100000"), "nothing came off, nothing written off")

    def test_each_lowered_line_honours_the_flag_beside_a_raised_one(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_each_lowered_line_honours_the_flag_beside_a_raised_one"""
        self.count_everything({self.pp1: 5, self.qq1: 4})

        self.count_bags({self.pp1: 1, self.qq1: 9}, reuse_other_material=False)

        self.assertEqual(inv.on_hand_bags(self.pp1, inv.latest_snapshot_date()), 1)
        self.assertEqual(self._available(), Decimal("99900"), "pp1's 80 leaflets are lost")
        self.assertEqual(self._booked(), Decimal("99920"))

    def test_a_raise_does_not_offset_a_discard_in_the_same_material_pool(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_a_raise_does_not_offset_a_discard_in_the_same_material_pool"""
        # Ten 1 kg packets a bag: the same leaflet pool as pp1's twenty.
        pp2 = add_packaging(self.product, packet_weight=W1, packets=10, actor=self.su)
        self.count_bags({self.pp1: 5, pp2: 0})  # 100 leaflets used

        # pp1 drops 40 packets, pp2 packs 40: the pool's net usage is unchanged.
        self.count_bags({self.pp1: 3, pp2: 4}, reuse_other_material=False)

        self.assertEqual(self._booked(), Decimal("99960"), "pp1's 40 leaflets are written off")
        self.assertEqual(self._available(), Decimal("99860"))

        self.count_bags({self.pp1: 2, pp2: 6}, reuse_other_material=True)
        self.assertEqual(self._booked(), Decimal("99960"), "reuse writes nothing off")
        self.assertEqual(self._available(), Decimal("99860"), "-20 +20 leaflets")

    def test_a_packaging_at_zero_can_be_raised(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_a_packaging_at_zero_can_be_raised"""
        self.count_bags({self.pp1: 1}, reuse_other_material=False)
        self.assertEqual(self._booked(), Decimal("100000"))

        self.count_bags({self.pp1: 0}, reuse_other_material=False)  # zero is not a raise
        self.assertEqual(self._booked(), Decimal("99980"), "the 20 leaflets are written off")

    def test_the_floor_after_dispatches_decides_a_raise(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_the_floor_after_dispatches_decides_a_raise"""
        self.count_everything({self.pp1: 5, self.qq1: 0})
        self.dispatch(self.order(self.pp1, 2), self.pp1)  # 3 bags left on the floor

        self.count_bags({self.pp1: 4}, reuse_other_material=False)  # above 3: a raise
        self.assertEqual(self._booked(), Decimal("100000"), "the flag was ignored")

    def test_the_flag_defaults_to_reuse(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_the_flag_defaults_to_reuse"""
        self.count_bags({self.pp1: 5})
        self.count_bags({self.pp1: 8})  # raising is allowed by default
        self.assertEqual(self._available(), Decimal("99840"))

    # -- loose packets -----------------------------------------------------------

    def test_loose_packets_follow_the_same_rules(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialTest::test_loose_packets_follow_the_same_rules"""
        self.count_loose(self.product, 50)
        self.assertEqual(self._available(), Decimal("99950"))

        self.count_loose(self.product, 51, reuse_other_material=False)  # a raise: flag ignored
        self.assertEqual(self._available(), Decimal("99949"))

        self.count_loose(self.product, 20, reuse_other_material=False)
        self.assertEqual(self._available(), Decimal("99949"), "31 packets' leaflets are lost")

        self.count_loose(self.product, 10)  # reuse: these 10 packets' leaflets come back
        self.assertEqual(self._available(), Decimal("99959"))


class DiscardedMaterialStaysSpentTest(_AvailableLeaflets, LedgerWorldTestCase):
    """tests/test_reuse_other_material.py::DiscardedMaterialStaysSpentTest"""

    def setUp(self):
        super().setUp()
        self.raw(self.product, "100000")
        self.raw(self.other_product, "100000")
        self.pouches("100", recipe=self.recipe_p)  # exactly 5 bags' worth of leaflets
        self.pouches("100000", recipe=self.recipe_q)
        self.count_everything({self.pp1: 5, self.qq1: 0})

    def test_a_discard_leaves_nothing_to_pack_with(self):
        """tests/test_reuse_other_material.py::DiscardedMaterialStaysSpentTest::test_a_discard_leaves_nothing_to_pack_with"""
        self.count_bags({self.pp1: 2}, reuse_other_material=False)

        with self.assertRaises(ValueError) as caught:
            self.count_bags({self.pp1: 3})
        self.assertIn("Not enough packing material", str(caught.exception))

    def test_discarding_everything_retires_the_emptied_lot(self):
        """tests/test_reuse_other_material.py::DiscardedMaterialStaysSpentTest::test_discarding_everything_retires_the_emptied_lot"""
        self.count_bags({self.pp1: 0}, reuse_other_material=False)

        self.assertFalse(InwardOtherMaterial.objects.filter(recipe=self.recipe_p).exists())
        retired = InwardOtherMaterial.all_objects.get(recipe=self.recipe_p)
        self.assertTrue(retired.is_deleted)
        self.assertEqual(retired.quantity, Decimal("100"), "the booked figure is kept")
        self.assertEqual(self._available(), Decimal("0"))

    def test_a_reuse_reduction_frees_the_material_to_pack_again(self):
        """tests/test_reuse_other_material.py::DiscardedMaterialStaysSpentTest::test_a_reuse_reduction_frees_the_material_to_pack_again"""
        self.count_bags({self.pp1: 2})

        self.count_bags({self.pp1: 5})  # the 60 leaflets came back, so this fits


class ReuseOtherMaterialApiTest(_AvailableLeaflets, LedgerWorldTestCase):
    """tests/test_reuse_other_material.py::ReuseOtherMaterialApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin_user = User.objects.create_user(
            phone_number="9510000099",
            name="Count Admin",
            is_verified=True,
            created_by=cls.su,
            verified_by=cls.su,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.su, can_update_stock_count=True)

    def setUp(self):
        super().setUp()
        self.raw(self.product, "100000")
        self.pouches("100000")
        self.api = APIClient()
        self.api.force_login(self.admin_user)
        self.count_bags({self.pp1: 5})

    def test_bag_patch_without_reuse_discards_and_ignores_the_flag_on_a_raise(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialApiTest::test_bag_patch_without_reuse_discards_and_ignores_the_flag_on_a_raise"""
        raised = self.api.patch(
            BAG_URL,
            {"counts": {self.pp1.public_id: 6}, "reuse_other_material": False},
            format="json",
        )
        self.assertEqual(raised.status_code, status.HTTP_200_OK, raised.data)
        self.assertEqual(self._available(), Decimal("99880"))

        lowered = self.api.patch(
            BAG_URL,
            {"counts": {self.pp1.public_id: 2}, "reuse_other_material": False},
            format="json",
        )
        self.assertEqual(lowered.status_code, status.HTTP_200_OK, lowered.data)
        self.assertEqual(self._available(), Decimal("99880"))

    def test_bag_patch_defaults_to_reuse(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialApiTest::test_bag_patch_defaults_to_reuse"""
        response = self.api.patch(BAG_URL, {"counts": {self.pp1.public_id: 2}}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self._available(), Decimal("99960"))

    def test_bag_post_without_reuse_discards_what_the_payload_leaves_out(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialApiTest::test_bag_post_without_reuse_discards_what_the_payload_leaves_out"""
        # A full upload records every packaging the payload omits as zero.
        response = self.api.post(
            BAG_URL, {"counts": {}, "reuse_other_material": False}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self._available(), Decimal("99900"))

    def test_loose_patch_honours_the_flag(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialApiTest::test_loose_patch_honours_the_flag"""
        self.count_loose(self.product, 40)
        line = {"product": self.product.public_id, "packet_weight": "1.000"}

        raised = self.api.patch(
            LOOSE_URL,
            {"counts": [{**line, "packets": 41}], "reuse_other_material": False},
            format="json",
        )
        self.assertEqual(raised.status_code, status.HTTP_200_OK, raised.data)

        lowered = self.api.patch(
            LOOSE_URL,
            {"counts": [{**line, "packets": 10}], "reuse_other_material": False},
            format="json",
        )
        self.assertEqual(lowered.status_code, status.HTTP_200_OK, lowered.data)
        self.assertEqual(self._available(), Decimal("99859"), "100 in bags + 41 loose, kept spent")

    def test_a_non_boolean_flag_is_refused(self):
        """tests/test_reuse_other_material.py::ReuseOtherMaterialApiTest::test_a_non_boolean_flag_is_refused"""
        response = self.api.patch(
            BAG_URL,
            {"counts": {self.pp1.public_id: 2}, "reuse_other_material": "maybe"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
