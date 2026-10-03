"""Shared fixture world for the product stock ledger tests.

Two products (``P`` and ``Q``) that both pack with the same material type
(``pouch``), a party, a client with an address, and helpers that drive every
write through the real operations layer -- which is what records the ledger.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations
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
    StockEvent,
)
from aggregator.OrderOperations import create_order, dispatch_order, verify_order
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import SalesPerson, User
from tests.common import DMLTestCase, book_raw_material

TODAY = datetime.date.today()
W1 = Decimal("1.000")


class LedgerWorldTestCase(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.sp_user = User.objects.create_user(
            "9510000001", "Ledger Sales", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        country = Country.objects.get(name="India")
        state = State.objects.get(name="Gujarat", country=country)
        cls.city = City.objects.get(name="Surat", state=state)
        pincode, _ = Pincode.objects.get_or_create(
            code="395003", city=cls.city, defaults={"created_by": cls.su}
        )
        SalesPerson.objects.create(user=cls.sp_user, city=cls.city, created_by=cls.su)
        cls.address = Address.objects.create(
            address_line_1="1 Ledger Rd", pincode=pincode, city=cls.city,
            state=state, country=country, created_by=cls.su,
        )
        cls.client_obj = create_client(
            company_name="Ledger Traders", gst_number="27AAPFU0939F1ZV", actor=cls.sp_user
        )
        add_client_address(cls.client_obj, cls.address, cls.sp_user, is_primary=True)
        cls.party = Party.objects.create(name="Ledger Party", city=cls.city, created_by=cls.su)

        stage = Stage.by_id(StageIds.BREEDER)
        cls.product = create_product(
            name="Ledger P", crop="Maize", stage=stage,
            selling_price=Decimal("100.00"), actor=cls.su,
        )
        cls.other_product = create_product(
            name="Ledger Q", crop="Maize", stage=stage,
            selling_price=Decimal("100.00"), actor=cls.su,
        )
        cls.pp1 = add_packaging(cls.product, packet_weight=W1, packets=20, actor=cls.su)
        cls.qq1 = add_packaging(cls.other_product, packet_weight=W1, packets=10, actor=cls.su)
        # The seeded type: creating one would burn an id other tests count on.
        cls.pouch = OtherMaterialType.objects.get(name="leaflets")
        cls.recipe_p = OtherMaterialRecipe.objects.create(
            product=cls.product, material_type=cls.pouch, packet_weight=W1,
            quantity=Decimal("1.000"), created_by=cls.su,
        )
        cls.recipe_q = OtherMaterialRecipe.objects.create(
            product=cls.other_product, material_type=cls.pouch, packet_weight=W1,
            quantity=Decimal("2.000"), created_by=cls.su,
        )

    # -- stock helpers -----------------------------------------------------------

    def raw(self, product, kg):
        return book_raw_material(product, Decimal(kg), actor=self.su)

    def pouches(self, quantity, recipe=None):
        return InwardOperations.create_other_lot(
            party=self.party, recipe=recipe or self.recipe_p,
            quantity=Decimal(quantity), actor=self.su,
        )

    def count_bags(self, counts: dict[ProductPackaging, int], *, day=None, **kwargs):
        """A bag count of exactly ``counts``; every other packaging stays unnamed."""
        return inv.record_stock_counts(
            counts=counts, actor=self.su, snapshot_date=day, **kwargs
        )

    def count_everything(self, counts: dict[ProductPackaging, int], *, day=None):
        """A complete count: ``counts`` plus zero for every other packaging."""
        full = {**dict.fromkeys(ProductPackaging.objects.all(), 0), **counts}
        return inv.record_stock_counts(counts=full, actor=self.su, snapshot_date=day)

    def count_loose(self, product, packets, *, weight=W1, day=None, **kwargs):
        return inv.record_loose_stocks(
            counts={(product, weight): packets},
            actor=self.su,
            snapshot_date=day,
            **kwargs,
        )

    def order(self, packaging, quantity, *, verify=True):
        order = create_order(
            client=self.client_obj, delivery_address=self.address, actor=self.sp_user,
            items=[{"product_packaging": packaging, "quantity": quantity}],
        )
        if verify:
            verify_order(order, self.su)
        return order

    def dispatch(self, order, packaging, *, shipped=None):
        return dispatch_order(
            order, actor=self.su, from_city=self.city, driver_name="Ramesh",
            driver_number="9876500009", vehicle_number="GJ05AB1234",
            lot_numbers={packaging.public_id: "LOT-1"},
            quantities=None if shipped is None else {packaging.public_id: shipped},
        )

    def custom_order(self, product, packets):
        return create_custom_order(
            client=self.client_obj, delivery_address=self.address, actor=self.su,
            items=[{"product": product, "packet_weight": W1, "packets": packets}],
        )

    def dispatch_custom(self, order, product):
        return dispatch_custom_order(
            order, actor=self.su, from_city=self.city, driver_name="Ramesh",
            driver_number="9876500009", vehicle_number="GJ05AB1234",
            lot_numbers={(product.public_id, W1): "LOT-C"},
        )

    # -- reading the ledger ------------------------------------------------------

    def marker(self) -> int:
        """The id of the latest event, to ask what was written after this point."""
        return StockEvent.objects.order_by("-pk").values_list("pk", flat=True).first() or 0

    def events_since(self, marker: int, product=None) -> list[StockEvent]:
        events = StockEvent.objects.filter(pk__gt=marker).order_by("pk")
        if product is not None:
            events = events.filter(product=product)
        return list(events.prefetch_related("lines"))

    def kinds_since(self, marker: int, product=None) -> list[tuple[str, str]]:
        from aggregator.models import StockEventDetail, StockEventType

        return [
            (StockEventType(event.event_type).name, StockEventDetail(event.detail).name)
            for event in self.events_since(marker, product)
        ]
