"""The product stock ledger's golden worked example (PRD section 6.1).

One product, two days, fifteen steps. Every row of the report is asserted --
the full running state of the bag, loose, raw and packing-material pools -- and
so are the ``D2..D2`` opening balance and the closing balance. The ledger is
also checked against the live stock figures after every step.

Run: bash scripts/run.sh test-serial tests/test_stock_ledger_golden.py
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations, StockLedgerOperations
from aggregator.ClientOperations import add_client_address, create_client
from aggregator.CustomOrderOperations import create_custom_order, dispatch_custom_order
from aggregator.models import (
    Address,
    City,
    Country,
    OtherMaterialRecipe,
    OtherMaterialType,
    Party,
    Pincode,
    ProductPackaging,
    Stage,
    StageIds,
    State,
    Status,
    StockEvent,
)
from aggregator.OrderOperations import create_order, dispatch_order, verify_order
from aggregator.ProductOperations import add_packaging, create_product
from aggregator.StockLedgerReport import product_ledger_rows
from authentication.models import SalesPerson, User
from tests.common import DMLTestCase

D1 = datetime.date.today()
D2 = D1 + datetime.timedelta(days=1)
W1 = Decimal("1.000")


def at(day: datetime.date, hour: int, minute: int = 0) -> datetime.datetime:
    return datetime.datetime.combine(
        day, datetime.time(hour, minute), tzinfo=datetime.datetime.now().astimezone().tzinfo
    )


class StockLedgerGoldenTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.sp_user = User.objects.create_user(
            "9500000001", "Sales Person", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        country = Country.objects.get(name="India")
        state = State.objects.get(name="Gujarat", country=country)
        cls.city = City.objects.get(name="Surat", state=state)
        cls.city2 = City.objects.get(name="Ahmedabad", state=state)
        pincode, _ = Pincode.objects.get_or_create(
            code="395003", city=cls.city, defaults={"created_by": cls.su}
        )
        SalesPerson.objects.create(user=cls.sp_user, city=cls.city, created_by=cls.su)
        address = Address.objects.create(
            address_line_1="1 Ledger Rd", pincode=pincode, city=cls.city,
            state=state, country=country, created_by=cls.su,
        )
        cls.client_obj = create_client(
            company_name="Ledger Traders", gst_number="27AAPFU0939F1ZV", actor=cls.sp_user
        )
        add_client_address(cls.client_obj, address, cls.sp_user, is_primary=True)
        cls.address = address

        cls.product = create_product(
            name="Golden Maize", crop="Maize", stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("100.00"), actor=cls.su,
        )
        cls.pp1 = add_packaging(cls.product, packet_weight=W1, packets=20, actor=cls.su)
        # The seeded type: creating one would burn an id other tests count on.
        cls.pouch = OtherMaterialType.objects.get(name="leaflets")
        cls.recipe_a = OtherMaterialRecipe.objects.create(
            product=cls.product, material_type=cls.pouch, packet_weight=W1,
            quantity=Decimal("1.000"), created_by=cls.su,
        )
        cls.party = Party.objects.create(name="Golden Party", city=cls.city, created_by=cls.su)

    # -- the script ------------------------------------------------------------

    def _stamp(self, day, hour, minute=0):
        """Move the events written since the last stamp to a scripted time."""
        StockEvent.objects.filter(pk__gt=self.last_event_id).update(
            occurred_at=at(day, hour, minute)
        )
        self.last_event_id = StockEvent.objects.order_by("-pk").values_list("pk", flat=True).first() or 0
        self.assertEqual(StockLedgerOperations.check_ledger(), [])

    def _lot_status(self, lot, code):
        return InwardOperations.update_raw_lot(
            lot,
            {"status": Status.objects.get(code=code), "effective_date": D1},
            self.su,
        )

    def _bag_count(self, bags, day, *, everything=False):
        counts = {self.pp1: bags}
        if everything:
            # Verifying an order needs a complete count, seeded packagings included.
            counts = {**dict.fromkeys(ProductPackaging.objects.all(), 0), **counts}
        return inv.record_stock_counts(counts=counts, actor=self.su, snapshot_date=day)

    def test_the_golden_example(self):
        """tests/test_stock_ledger_golden.py::StockLedgerGoldenTest::test_the_golden_example"""
        StockLedgerOperations.seed_ledger()
        self.last_event_id = 0
        self._stamp(D1, 0, 0)

        # 1-2: raw lots in use and rejected.
        lot1 = InwardOperations.create_raw_lot(
            product=self.product, party=self.party, lot_no="IR-1",
            quantity_kg=Decimal("500.000"), lab_sampling_date=D1, actor=self.su,
        )
        self._lot_status(lot1, "IN_USE")
        self._stamp(D1, 9, 0)
        lot2 = InwardOperations.create_raw_lot(
            product=self.product, party=self.party, lot_no="IR-2",
            quantity_kg=Decimal("100.000"), lab_sampling_date=D1, actor=self.su,
        )
        self._lot_status(lot2, "RAW_MATERIAL_REJECTED")
        self._stamp(D1, 9, 30)
        # 3: pouches in.
        InwardOperations.create_other_lot(
            party=self.party, recipe=self.recipe_a, quantity=Decimal("1000"), actor=self.su
        )
        self._stamp(D1, 9, 40)
        # 4-5: counts.
        self._bag_count(10, D1, everything=True)
        self._stamp(D1, 10, 0)
        inv.record_loose_stocks(counts={(self.product, W1): 30}, actor=self.su, snapshot_date=D1)
        self._stamp(D1, 10, 5)
        # 6: ORD-1 for 4 bags, verified.
        order = create_order(
            client=self.client_obj, delivery_address=self.address, actor=self.sp_user,
            items=[{"product_packaging": self.pp1, "quantity": 4}],
        )
        verify_order(order, self.su)
        self._stamp(D1, 11, 0)
        # 7: CORD-1 for 5 loose packets.
        custom = create_custom_order(
            client=self.client_obj, delivery_address=self.address, actor=self.su,
            items=[{"product": self.product, "packet_weight": W1, "packets": 5}],
        )
        self._stamp(D1, 12, 0)
        # 8: ORD-1 dispatched, 3 of 4 bags.
        dispatch_order(
            order, actor=self.su, from_city=self.city, driver_name="Ramesh",
            driver_number="9876500009", vehicle_number="GJ05AB1234",
            lot_numbers={self.pp1.public_id: "LOT-1"},
            quantities={self.pp1.public_id: 3},
        )
        self._stamp(D1, 13, 0)
        # 9: 20 kg wasted.
        inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("20.000"), reason="spill", actor=self.su
        )
        self._stamp(D1, 14, 0)
        # 10: D2 morning recount after yesterday's dispatches -- nothing packed.
        self._bag_count(7, D2)
        self._stamp(D2, 9, 0)
        # 11: pack 2 more bags.
        self._bag_count(9, D2)
        self._stamp(D2, 10, 0)
        # 12: CORD-1 dispatched in full.
        dispatch_custom_order(
            custom, actor=self.su, from_city=self.city, driver_name="Ramesh",
            driver_number="9876500009", vehicle_number="GJ05AB1234",
            lot_numbers={(self.product.public_id, W1): "LOT-C"},
        )
        self._stamp(D2, 11, 0)
        # 13: recipe A replaced by B (2 pouches a packet) -- no row.
        self.recipe_a.mark_deleted(self.su)
        OtherMaterialRecipe.objects.create(
            product=self.product, material_type=self.pouch, packet_weight=W1,
            quantity=Decimal("2.000"), created_by=self.su,
        )
        self._stamp(D2, 12, 0)
        self.assertFalse(StockEvent.objects.filter(occurred_at=at(D2, 12, 0)).exists())
        # 14: pack 1 more bag, at recipe B.
        self._bag_count(10, D2)
        self._stamp(D2, 13, 0)
        # 15: unpack 2 bags: LIFO takes B first, then A.
        self._bag_count(8, D2)
        self._stamp(D2, 14, 0)

        rows = [
            row
            for row in product_ledger_rows(self.product, D1, D2)
            if row["event"] not in ("LEDGER_START", "OPENING_BALANCE", "CLOSING_BALANCE")
        ]
        expected = [
            # event, bags oh/res/con/avail, loose, raw inc/packed/rej/waste/avail, pouch inc/packed/avail
            ("INWARD_OPERATIONS", (0, 0, 0, 0), (0, 0, 0, 0), ("500", "0", "0", "0", "500"), ("0", "0", "0")),
            ("INWARD_OPERATIONS", (0, 0, 0, 0), (0, 0, 0, 0), ("500", "0", "100", "0", "500"), ("0", "0", "0")),
            ("INWARD_OPERATIONS", (0, 0, 0, 0), (0, 0, 0, 0), ("500", "0", "100", "0", "500"), ("1000", "0", "1000")),
            ("PACKED", (10, 0, 0, 10), (0, 0, 0, 0), ("500", "200", "100", "0", "300"), ("1000", "200", "800")),
            ("PACKED", (10, 0, 0, 10), (30, 0, 0, 30), ("500", "230", "100", "0", "270"), ("1000", "230", "770")),
            ("ORDER_CONFIRMED", (10, 4, 0, 6), (30, 0, 0, 30), ("500", "230", "100", "0", "270"), ("1000", "230", "770")),
            ("ORDER_CONFIRMED", (10, 4, 0, 6), (30, 5, 0, 25), ("500", "230", "100", "0", "270"), ("1000", "230", "770")),
            ("ORDER_DISPATCHED", (10, 1, 3, 6), (30, 5, 0, 25), ("500", "230", "100", "0", "270"), ("1000", "230", "770")),
            ("RAW_WASTED", (10, 1, 3, 6), (30, 5, 0, 25), ("500", "230", "100", "20", "250"), ("1000", "230", "770")),
            ("STOCK_COUNTED", (7, 1, 0, 6), (30, 5, 0, 25), ("500", "230", "100", "20", "250"), ("1000", "230", "770")),
            ("PACKED", (9, 1, 0, 8), (30, 5, 0, 25), ("500", "270", "100", "20", "210"), ("1000", "270", "730")),
            ("ORDER_DISPATCHED", (9, 1, 0, 8), (30, 0, 5, 25), ("500", "270", "100", "20", "210"), ("1000", "270", "730")),
            ("PACKED", (10, 1, 0, 9), (30, 0, 5, 25), ("500", "290", "100", "20", "190"), ("1000", "310", "690")),
            ("STOCK_ADJUSTED", (8, 1, 0, 7), (30, 0, 5, 25), ("500", "250", "100", "20", "230"), ("1000", "250", "750")),
        ]
        self.assertEqual([row["event"] for row in rows], [item[0] for item in expected])
        for index, (row, item) in enumerate(zip(rows, expected, strict=True), start=1):
            with self.subTest(step=index, event=item[0]):
                self.assertEqual(self._figures(row), item[1:])

        # The report's own arithmetic: row k + change(k+1) == row k+1.
        self.assertEqual(self._figures(rows[-1]), expected[-1][1:])

        closing = product_ledger_rows(self.product, D1, D2)[-1]
        self.assertEqual(self._figures(closing), expected[-1][1:])

        # A D2..D2 report opens where D1 ended, and closes where D2 does.
        d2 = product_ledger_rows(self.product, D2, D2)
        self.assertEqual(
            self._figures(d2[0]),
            ((10, 1, 3, 6), (30, 5, 0, 25), ("500", "230", "100", "20", "250"), ("1000", "230", "770")),
        )
        self.assertEqual(self._figures(d2[-1]), expected[-1][1:])

        # Final recipe layers: A 220 packets on the bag row, A 30 on the loose row.
        self.assertEqual(inv.other_material_used([self.pouch.pk])[self.pouch.pk], Decimal("250.000"))

    @staticmethod
    def _figures(row):
        bag = row["bag_pools"][0]
        loose = row["packet_pools"][0]
        raw = row["raw_material"]
        pouch = row["other_materials"][0]
        return (
            (bag["on_hand"], bag["reserved"], bag["consumed"], bag["available"]),
            (loose["on_hand"], loose["reserved"], loose["consumed"], loose["available"]),
            tuple(
                str(Decimal(raw[name]).quantize(Decimal("1")))
                for name in ("incoming", "packed", "rejected", "wasted", "available")
            ),
            tuple(
                str(Decimal(pouch[name]).quantize(Decimal("1")))
                for name in ("incoming", "packed", "available")
            ),
        )
