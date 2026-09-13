"""Sales-admin order reads: ``GET /api/sales-admin/orders/`` and
``GET /api/sales-admin/order/<public_id>``.

Session-only admin endpoints, exercised over the ``WebApiTestCase`` baseline
(DML-seeded, browser session). Orders are seeded through
``OrderOperations.create_order`` rather than the booking endpoint -- booking is
covered in ``tests/android/test_bag_orders.py``.

Authentication and role gating are proven once in
``tests/test_view_contracts.py``; pagination and the generic filter/sort parsing
in ``tests/android/test_clients.py`` and ``tests/test_paginated_filters.py``.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import create_client_with_details
from aggregator.models import (
    City,
    Country,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import create_order
from authentication.models import Admin, SalesPerson
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
ORDERS_URL = "/api/sales-admin/orders/"
ORDER_URL = "/api/sales-admin/order/{public_id}"


class SalesAdminOrderReadApiTest(WebApiTestCase):
    """Cover listing every order, the five filters, both sorts and the detail view.

    tests/test_admin_order_api.py::SalesAdminOrderReadApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Two sales people with a client each, across two cities, and two bags."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        # India / Gujarat / Surat / Ahmedabad are part of the dml.sql baseline.
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.other_city = City.objects.get(name="Ahmedabad", state=cls.state)

        cls.admin_user = User.objects.create_user(
            phone_number="9000000401",
            name="Sales Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)

        cls.sales_one = cls._sales_person("9000000402", "Sales One")
        cls.sales_two = cls._sales_person("9000000403", "Sales Two")

        cls.acme = cls._client(
            cls.sales_one, "Acme Seeds", "27AAPFU0939F1ZV", cls.city, "395007"
        )
        cls.beta = cls._client(
            cls.sales_two, "Beta Seeds", "27AAPFU0939F1ZB", cls.other_city, "380001"
        )

        cls.alpha_bag = cls._bag("Alpha Seed", Decimal("1000.00"), packets=10)
        cls.beta_bag = cls._bag("Beta Seed", Decimal("500.00"), packets=5)
        cls.alpha_product = cls.alpha_bag.product
        cls.beta_product = cls.beta_bag.product

    @classmethod
    def _sales_person(cls, phone, name):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(user=user, city=cls.city, created_by=cls.superuser)
        return user

    @classmethod
    def _client(cls, actor, company_name, gst, city, pincode):
        return create_client_with_details(
            company_name=company_name,
            company_phone="9876543210",
            gst_number=gst,
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "line_2": "",
                    "pincode": pincode,
                    "city": city,
                    "state": cls.state,
                    "country": cls.country,
                    "label": "Warehouse",
                    "is_primary": True,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": f"{company_name} Transport"}],
            actor=actor,
        )

    @classmethod
    def _bag(cls, product_name, price, *, packets):
        product = Product.objects.create(
            name=product_name,
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )
        return ProductPackaging.objects.create(
            product=product,
            packet_weight=Decimal("1.000"),
            packets=packets,
            selling_price=price,
            created_by=cls.superuser,
        )

    # -- helpers --------------------------------------------------------------

    def _order(self, client_row, lines, *, actor, status_id=StatusIds.BOOKED, agency=None):
        return create_order(
            client=client_row,
            delivery_address=client_row.client_addresses.first().address,
            actor=actor,
            items=[
                {"product_packaging": packaging, "quantity": quantity}
                for packaging, quantity in lines
            ],
            status=status_id,
            transport_agency=agency,
        )

    def _seed_orders(self):
        """Three orders across two sales people, two clients and two cities.

        Oldest to newest: acme/alpha (1000), beta/beta (1500), acme/both (2500).
        """
        agency = self.acme.client_transport_agencies.first().transport_agency
        self.first = self._order(
            self.acme, [(self.alpha_bag, 1)], actor=self.sales_one, agency=agency
        )
        self.second = self._order(
            self.beta,
            [(self.beta_bag, 3)],
            actor=self.sales_two,
            status_id=StatusIds.ON_HOLD,
        )
        self.third = self._order(
            self.acme, [(self.alpha_bag, 2), (self.beta_bag, 1)], actor=self.sales_one
        )
        self.login_as(self.admin_user)

    def _ids(self, response):
        return [row["public_id"] for row in response.data["results"]]

    def _filter_entry(self, response, name):
        return next(
            f for f in response.data["available_filters"] if f["filter"] == name
        )

    # -- listing --------------------------------------------------------------

    def test_the_card_carries_everything_the_admin_screen_needs(self):
        """One request, asserted across the whole card and both catalogues.

        tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_the_card_carries_everything_the_admin_screen_needs
        """
        self._seed_orders()

        response = self.client.get(ORDERS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Every sales person's orders, not just one caller's.
        self.assertEqual(response.data["total_count"], 3)
        self.assertEqual(
            self._ids(response),
            [self.third.public_id, self.second.public_id, self.first.public_id],
        )
        self.assertEqual(
            [(f["filter"], f["kind"]) for f in response.data["available_filters"]],
            [
                ("created_by", "select"),
                ("client", "select"),
                ("product", "select"),
                ("city_id", "select"),
                ("status", "select"),
            ],
        )
        self.assertEqual(
            [s["sort"] for s in response.data["available_sorts"]],
            ["created_at", "price"],
        )

        card = next(
            row
            for row in response.data["results"]
            if row["public_id"] == self.first.public_id
        )
        self.assertEqual(card["client"]["company_name"], "Acme Seeds")
        self.assertEqual(card["client_created_by"], "Sales One")
        self.assertEqual(card["created_by"], "Sales One")
        self.assertIsNone(card["verified_by"])
        self.assertEqual(card["status"], "BOOKED")
        self.assertEqual(card["city"]["name"], "Surat")
        self.assertIn("Ring Road", card["delivery_address"])
        self.assertEqual(card["transport_agency"]["name"], "Acme Seeds Transport")
        self.assertEqual(card["dispatch_mode"], "AGENCY")
        self.assertEqual(card["total_amount"], "1000.00")
        self.assertEqual(card["total_packets"], 10)
        # One entry per line: the bag ordered, how many, and the product in it.
        self.assertEqual(len(card["packagings"]), 1)
        bag = card["packagings"][0]
        self.assertEqual(bag["public_id"], self.alpha_bag.public_id)
        self.assertEqual(bag["quantity"], 1)
        self.assertEqual(bag["packets"], 10)
        self.assertEqual(bag["product"]["name"], "Alpha Seed")
        self.assertEqual(bag["product"]["public_id"], self.alpha_product.public_id)
        self.assertIn("image_url", bag["product"])

    def test_the_list_spans_every_sales_person(self):
        """The admin sees both sales people, and each is a filter option.

        tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_the_list_spans_every_sales_person
        """
        self._seed_orders()

        response = self.client.get(ORDERS_URL)

        self.assertEqual(
            sorted(row["created_by"] for row in response.data["results"]),
            ["Sales One", "Sales One", "Sales Two"],
        )
        self.assertEqual(
            [o["label"] for o in self._filter_entry(response, "created_by")["options"]],
            ["Sales One", "Sales Two"],
        )

    # -- filtering ------------------------------------------------------------

    def test_each_filter_narrows_the_list(self):
        """The five filters, one subTest each.

        tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_each_filter_narrows_the_list
        """
        self._seed_orders()

        cases = [
            (
                "sales person",
                {"created_by": str(self.sales_one.id)},
                {self.first.public_id, self.third.public_id},
            ),
            (
                "client",
                {"client": str(self.beta.id)},
                {self.second.public_id},
            ),
            (
                "product",
                {"product": str(self.alpha_product.id)},
                {self.first.public_id, self.third.public_id},
            ),
            (
                "city",
                {"city_id": str(self.other_city.id)},
                {self.second.public_id},
            ),
            (
                "status",
                {"status": "ON_HOLD"},
                {self.second.public_id},
            ),
        ]
        for label, query, expected in cases:
            with self.subTest(filter=label):
                response = self.client.get(ORDERS_URL, query)
                self.assertEqual(set(self._ids(response)), expected)

    def test_filters_combine(self):
        """tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_filters_combine"""
        self._seed_orders()

        response = self.client.get(
            ORDERS_URL,
            {"created_by": str(self.sales_one.id), "product": str(self.beta_product.id)},
        )

        self.assertEqual(self._ids(response), [self.third.public_id])

    def test_the_product_filter_does_not_shrink_the_order_total(self):
        """Filtering to one product still reports the order's *whole* total.

        The regression guard for summing over the item join: ``?product=``
        narrows that join, so a join aggregate would total only the matching
        line instead of the order.

        tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_the_product_filter_does_not_shrink_the_order_total
        """
        self._seed_orders()

        response = self.client.get(ORDERS_URL, {"product": str(self.beta_product.id)})

        mixed = next(
            row
            for row in response.data["results"]
            if row["public_id"] == self.third.public_id
        )
        # Two lines: 2 alpha bags at 1000 plus 1 beta bag at 500.
        self.assertEqual(mixed["total_amount"], "2500.00")
        self.assertEqual(len(mixed["packagings"]), 2)

    def test_the_option_lists_name_only_values_that_exist(self):
        """A sales person with no orders is not offered as a filter value.

        tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_the_option_lists_name_only_values_that_exist
        """
        self._sales_person("9000000404", "Sales Three")
        self._seed_orders()

        response = self.client.get(ORDERS_URL)

        labels = [o["label"] for o in self._filter_entry(response, "created_by")["options"]]
        self.assertNotIn("Sales Three", labels)
        self.assertEqual(
            [o["label"] for o in self._filter_entry(response, "city_id")["options"]],
            ["Ahmedabad", "Surat"],
        )

    def test_an_unknown_status_is_rejected(self):
        """tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_an_unknown_status_is_rejected"""
        self._seed_orders()

        response = self.client.get(ORDERS_URL, {"status": "SHIPPED"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown status", response.data["detail"])

    # -- sorting --------------------------------------------------------------

    def test_sorting_by_price_and_created_at(self):
        """``price`` orders on the order's total, in both directions.

        tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_sorting_by_price_and_created_at
        """
        self._seed_orders()

        cheapest_first = [
            self.first.public_id,  # 1000.00
            self.second.public_id,  # 1500.00
            self.third.public_id,  # 2500.00
        ]
        cases = [
            ("price ascending", {"sort": "price"}, cheapest_first),
            ("price descending", {"sort": "-price"}, list(reversed(cheapest_first))),
            ("oldest first", {"sort": "created_at"}, cheapest_first),
        ]
        for label, query, expected in cases:
            with self.subTest(sort=label):
                response = self.client.get(ORDERS_URL, query)
                self.assertEqual(self._ids(response), expected)

    # -- detail ---------------------------------------------------------------

    def test_the_detail_embeds_the_whole_client_and_every_line(self):
        """The client block carries its addresses and agencies *with ids*.

        tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_the_detail_embeds_the_whole_client_and_every_line
        """
        self._seed_orders()

        response = self.client.get(ORDER_URL.format(public_id=self.third.public_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["public_id"], self.third.public_id)
        self.assertEqual(data["total_amount"], "2500.00")

        client = data["client"]
        self.assertEqual(client["company_name"], "Acme Seeds")
        self.assertEqual(client["created_by"], "Sales One")
        # The edit screen's pickers need a link id for every address and agency.
        self.assertTrue(client["addresses"])
        self.assertTrue(all(a["id"] for a in client["addresses"]))
        self.assertTrue(client["transport_agencies"])
        self.assertTrue(all(t["id"] for t in client["transport_agencies"]))

        self.assertEqual(len(data["items"]), 2)
        line = next(
            item
            for item in data["items"]
            if item["packaging"]["public_id"] == self.alpha_bag.public_id
        )
        self.assertEqual(line["quantity"], 2)
        self.assertEqual(line["negotiated_selling_price"], "1000.00")
        self.assertEqual(line["line_total"], "2000.00")
        self.assertEqual(line["packaging"]["product"]["name"], "Alpha Seed")

    def test_an_unknown_order_is_404(self):
        """tests/test_admin_order_api.py::SalesAdminOrderReadApiTest::test_an_unknown_order_is_404"""
        self._seed_orders()

        response = self.client.get(ORDER_URL.format(public_id="ORD-NOPE"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
