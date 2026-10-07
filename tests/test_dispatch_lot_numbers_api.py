"""Product-wise recent dispatch lot numbers.

``GET /api/sales-admin/dispatch-lot-numbers/`` groups by ``(lot, product)``: a
bag line's product comes from its packaging, a loose line's from its own
``product``. Authentication and role gating are proven once in
``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import create_client_with_details
from aggregator.models import (
    City,
    Country,
    DispatchEntry,
    DispatchEntryItem,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.OrderOperations import create_order
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
LOTS_URL = "/api/sales-admin/dispatch-lot-numbers/"


class DispatchLotNumbersApiTest(WebApiTestCase):
    """tests/test_dispatch_lot_numbers_api.py::DispatchLotNumbersApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        country = Country.objects.get(name="India")
        state = State.objects.get(name="Gujarat", country=country)
        cls.city = City.objects.get(name="Surat", state=state)

        cls.admin_user = User.objects.create_user(
            phone_number="9000000901",
            name="Lot Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)
        sales_person = User.objects.create_user(
            phone_number="9000000902",
            name="Lot Sales",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(user=sales_person, city=cls.city, created_by=cls.superuser)

        client = create_client_with_details(
            company_name="Lot Traders",
            company_phone="9876543210",
            gst_number="27AAPFU0939F1ZV",
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "line_2": "",
                    "pincode": "395007",
                    "city": cls.city,
                    "state": state,
                    "country": country,
                    "label": "Warehouse",
                    "is_primary": True,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": "Lot Transport"}],
            actor=sales_person,
        )

        def product(name):
            return Product.objects.create(
                name=name,
                crop_id=1,
                stage=Stage.by_id(StageIds.CERTIFIED),
                selling_price=Decimal("100.00"),
                created_by=cls.superuser,
            )

        cls.alpha = product("Alpha Lot Seed")
        cls.beta = product("Beta Lot Seed")
        cls.alpha_bag = ProductPackaging.objects.create(
            product=cls.alpha,
            packet_weight=Decimal("1.000"),
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=cls.superuser,
        )
        cls.beta_bag = ProductPackaging.objects.create(
            product=cls.beta,
            packet_weight=Decimal("1.000"),
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=cls.superuser,
        )

        address = client.client_addresses.first().address
        order = create_order(
            client=client,
            delivery_address=address,
            actor=sales_person,
            items=[{"product_packaging": cls.alpha_bag, "quantity": 1}],
        )
        entry = DispatchEntry.objects.create(
            order=order,
            client=client,
            client_address=address,
            dispatched_at=indian_now(),
            from_city=cls.city,
            to_city=cls.city,
        )

        def line(lot, minutes_ago, **kind):
            item = DispatchEntryItem.objects.create(
                dispatch_entry=entry,
                negotiated_selling_price=Decimal("10.00"),
                quantity=1,
                lot_number=lot,
                **kind,
            )
            # Pin the recency the ordering is judged on.
            DispatchEntryItem.objects.filter(pk=item.pk).update(
                created_at=indian_now() - timedelta(minutes=minutes_ago)
            )

        line("LOT-A", 30, product_packaging=cls.alpha_bag)  # bag line -> alpha
        line("LOT-A", 20, product_packaging=cls.beta_bag)  # same lot, other product
        line("LOT-B", 10, product=cls.beta, packet_weight=Decimal("0.500"))  # loose
        # A line with no lot number is never listed.
        line("", 1, product=cls.alpha, packet_weight=Decimal("0.250"))

    def setUp(self):
        super().setUp()
        self.login_as(self.admin_user)

    def _rows(self, **params):
        response = self.client.get(LOTS_URL, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["results"]

    def test_a_lot_used_for_two_products_is_listed_once_per_product(self):
        """tests/test_dispatch_lot_numbers_api.py::DispatchLotNumbersApiTest::test_a_lot_used_for_two_products_is_listed_once_per_product"""
        rows = self._rows()

        self.assertEqual(
            [(row["lot_number"], row["product_id"]) for row in rows],
            [
                ("LOT-B", self.beta.id),
                ("LOT-A", self.beta.id),
                ("LOT-A", self.alpha.id),
            ],
        )
        self.assertTrue(all("last_used_at" in row for row in rows))

    def test_a_bag_line_takes_its_product_from_the_packaging(self):
        """tests/test_dispatch_lot_numbers_api.py::DispatchLotNumbersApiTest::test_a_bag_line_takes_its_product_from_the_packaging"""
        rows = self._rows(q="LOT-A")

        self.assertEqual({row["product_id"] for row in rows}, {self.alpha.id, self.beta.id})

    def test_a_loose_line_takes_its_product_from_the_line(self):
        """tests/test_dispatch_lot_numbers_api.py::DispatchLotNumbersApiTest::test_a_loose_line_takes_its_product_from_the_line"""
        rows = self._rows(q="LOT-B")

        self.assertEqual(
            [(row["lot_number"], row["product_id"]) for row in rows],
            [("LOT-B", self.beta.id)],
        )

    def test_every_row_names_its_product(self):
        """tests/test_dispatch_lot_numbers_api.py::DispatchLotNumbersApiTest::test_every_row_names_its_product"""
        names = {row["product_id"]: row["product_name"] for row in self._rows()}

        self.assertEqual(
            names,
            {self.alpha.id: "Alpha Lot Seed", self.beta.id: "Beta Lot Seed"},
        )

    def test_the_limit_applies_per_product(self):
        """tests/test_dispatch_lot_numbers_api.py::DispatchLotNumbersApiTest::test_the_limit_applies_per_product"""
        rows = self._rows(limit=1)

        # beta has two lots (LOT-B newest) but keeps one; alpha keeps its one.
        self.assertEqual(
            [(row["lot_number"], row["product_id"]) for row in rows],
            [("LOT-B", self.beta.id), ("LOT-A", self.alpha.id)],
        )
