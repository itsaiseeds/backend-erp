"""Android order list endpoint: ``GET /android/api/v1/get-orders``.

Covers the caller scoping, the four filters (client / product / city / status),
the two sorts (created_at / price) and the card contents. Orders are seeded
through ``OrderOperations.create_order`` rather than the booking endpoint --
booking is covered in ``tests/android/test_bag_orders.py``.

Authentication and role gating are proven once in
``tests/test_view_contracts.py``; pagination and the generic filter parsing in
``tests/android/test_clients.py`` and ``tests/test_paginated_filters.py``.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import create_client_with_details
from aggregator.models import (
    City,
    Country,
    Order,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
    Status,
)
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import create_order
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.android.common import AndroidApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
GET_ORDERS_URL = "/android/api/v1/get-orders"


class AndroidOrderListApiTest(AndroidApiTestCase):
    """Cover listing, scoping, filtering and sorting the caller's orders.

    tests/android/test_orders.py::AndroidOrderListApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Two sales people, three clients across two cities, two bags."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        # India / Gujarat / Surat / Ahmedabad are part of the dml.sql baseline.
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.other_city = City.objects.get(name="Ahmedabad", state=cls.state)

        cls.sales_person = cls._sales_person("9000000301", "Sales One")
        cls.other_sales_person = cls._sales_person("9000000302", "Sales Two")

        cls.acme = cls._client(
            cls.sales_person, "Acme Seeds", "27AAPFU0939F1ZV", cls.city, "395007"
        )
        cls.beta = cls._client(
            cls.sales_person, "Beta Seeds", "27AAPFU0939F1ZB", cls.other_city, "380001"
        )
        cls.rival = cls._client(
            cls.other_sales_person, "Rival Seeds", "27AAPFU0939F1ZG", cls.city, "395007"
        )

        cls.alpha_bag = cls._bag(
            "Alpha Seed",
            Decimal("1000.00"),
            packets=10,
            image_url="/media/products/alpha.jpg",
        )
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
    def _bag(cls, product_name, price, *, packets, image_url="", packet_weight="1.000"):
        product = Product.objects.create(
            name=product_name,
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            image_url=image_url,
            created_by=cls.superuser,
        )
        return ProductPackaging.objects.create(
            product=product,
            packet_weight=Decimal(packet_weight),
            packets=packets,
            selling_price=price,
            created_by=cls.superuser,
        )

    # -- helpers --------------------------------------------------------------

    def _order(self, client_row, lines, *, actor=None, status_id=StatusIds.BOOKED):
        """Book one order; ``lines`` is ``[(packaging, quantity), ...]``."""
        return create_order(
            client=client_row,
            delivery_address=client_row.client_addresses.first().address,
            actor=actor or self.sales_person,
            items=[
                {"product_packaging": packaging, "quantity": quantity}
                for packaging, quantity in lines
            ],
            status=status_id,
        )

    def _seed_orders(self):
        """Three orders for the caller across two clients / cities / products,
        plus one belonging to the other sales person.

        Oldest to newest: acme/alpha (1000), beta/beta (1500), acme/both (2500).
        """
        self.first = self._order(self.acme, [(self.alpha_bag, 1)])
        self.second = self._order(
            self.beta, [(self.beta_bag, 3)], status_id=StatusIds.ON_HOLD
        )
        self.third = self._order(
            self.acme, [(self.alpha_bag, 2), (self.beta_bag, 1)]
        )
        self.theirs = self._order(
            self.rival, [(self.alpha_bag, 5)], actor=self.other_sales_person
        )
        self.login_as(self.sales_person)

    def _confirm(self, order, approver):
        """Move a booked order to CONFIRMED, the way the sales-admin API does.

        CONFIRMED is the *verified* state (``Order.is_verified``), and it may
        only be entered with the approver and the stamp on the row -- so this
        goes through ``full_clean`` rather than assigning the status blindly.
        """
        order.status = Status.by_id(StatusIds.CONFIRMED)
        order.verified_by = approver
        order.verified_at = indian_now()
        order.full_clean()
        order.save()
        return order

    def _sales_admin(self, phone, name):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=self.superuser,
            verified_by=self.superuser,
        )
        Admin.objects.create(user=user, created_by=self.superuser)
        return user

    def test_analytics_counts_orders_and_clients_and_kgs_per_product_in_the_window(self):
        """Counts are the caller's own, inside the window, zero-filled by status.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_analytics_counts_orders_and_clients_and_kgs_per_product_in_the_window
        """
        self._seed_orders()
        url = "/android/api/v1/analytics"
        everything = {
            "start_date_time": "2000-01-01T00:00:00Z",
            "end_date_time": "2999-01-01T00:00:00Z",
        }

        data = self.client.get(url, everything).data
        self.assertEqual(data["orders"]["total"], 3)
        self.assertEqual(
            data["orders"]["by_status"],
            {
                "BOOKED": 2,
                "UNDER_REVIEW": 0,
                "CONFIRMED": 0,
                "DISPATCHED": 0,
                "DELIVERED": 0,
                "ON_HOLD": 1,
                "REJECTED": 0,
            },
        )
        self.assertEqual(data["clients"]["total"], 2)  # the rival's client is not ours
        self.assertEqual(data["clients"]["by_status"], {"VERIFICATION_PENDING": 2, "VERIFIED": 0})

        # Kilograms grouped by product, heaviest first. Alpha is a 10kg bag and
        # beta a 5kg one. Alpha: 1 bag on ``first`` + 2 on ``third`` = 30kg,
        # all BOOKED. Beta: 3 bags on the ON_HOLD ``second`` + 1 on ``third``
        # = 20kg split across both statuses. The rival's 5 alpha bags are the
        # other sales person's.
        self.assertEqual(
            [(row["product"]["name"], row["total_kg"]) for row in data["products"]],
            [("Alpha Seed", "30.000"), ("Beta Seed", "20.000")],
        )
        alpha, beta = data["products"]
        self.assertEqual(alpha["product"]["public_id"], self.alpha_product.public_id)
        self.assertEqual(
            alpha["kg_by_status"],
            {
                "BOOKED": "30.000",
                "UNDER_REVIEW": "0.000",
                "CONFIRMED": "0.000",
                "DISPATCHED": "0.000",
                "DELIVERED": "0.000",
                "ON_HOLD": "0.000",
                "REJECTED": "0.000",
            },
        )
        self.assertEqual(beta["kg_by_status"]["ON_HOLD"], "15.000")
        self.assertEqual(beta["kg_by_status"]["BOOKED"], "5.000")

        # A window that closed before anything was created is all zeros.
        empty = self.client.get(
            url,
            {"start_date_time": "2000-01-01T00:00:00Z", "end_date_time": "2000-01-02T00:00:00Z"},
        ).data
        self.assertEqual(empty["orders"]["total"], 0)
        self.assertEqual(empty["clients"]["total"], 0)
        self.assertEqual(empty["products"], [])

        # Both bounds are required, in order.
        self.assertEqual(self.client.get(url).status_code, status.HTTP_400_BAD_REQUEST)
        inverted = {**everything, "start_date_time": "2999-01-02T00:00:00Z"}
        self.assertEqual(self.client.get(url, inverted).status_code, status.HTTP_400_BAD_REQUEST)

    def test_analytics_splits_the_kilograms_between_booked_and_confirmed(self):
        """Confirming an order moves its kg from one bucket to the next.

        The status drives the split, not the approver: the very same order
        weighs the same before and after, only landing under ``CONFIRMED``
        (the verified state) instead of ``BOOKED``. ``total_kg`` -- every status
        added up -- does not move.

        A three-line order spanning three products, one of them a 0.5kg packet:
        2 alpha (10kg) + 1 beta (5kg) + 1 half-kg trio (1.5kg), so a dropped or
        rounded fractional weight shows up rather than hides.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_analytics_splits_the_kilograms_between_booked_and_confirmed
        """
        approver = self._sales_admin("9000000388", "Sales Admin")
        half_kg_bag = self._bag("Gamma Seed", Decimal("900.00"), packets=3, packet_weight="0.500")
        order = self._order(
            self.acme,
            [(self.alpha_bag, 2), (self.beta_bag, 1), (half_kg_bag, 1)],
        )
        self.login_as(self.sales_person)
        url = "/android/api/v1/analytics"
        everything = {
            "start_date_time": "2000-01-01T00:00:00Z",
            "end_date_time": "2999-01-01T00:00:00Z",
        }

        before = {
            row["product"]["name"]: row for row in self.client.get(url, everything).data["products"]
        }
        self.assertEqual(
            [(name, row["total_kg"]) for name, row in before.items()],
            [("Alpha Seed", "20.000"), ("Beta Seed", "5.000"), ("Gamma Seed", "1.500")],
        )
        self.assertEqual(before["Alpha Seed"]["kg_by_status"]["BOOKED"], "20.000")
        self.assertEqual(before["Alpha Seed"]["kg_by_status"]["CONFIRMED"], "0.000")

        self._confirm(order, approver)

        after = {
            row["product"]["name"]: row for row in self.client.get(url, everything).data["products"]
        }
        self.assertEqual(after["Alpha Seed"]["kg_by_status"]["BOOKED"], "0.000")
        self.assertEqual(after["Alpha Seed"]["kg_by_status"]["CONFIRMED"], "20.000")
        self.assertEqual(after["Beta Seed"]["kg_by_status"]["CONFIRMED"], "5.000")
        self.assertEqual(after["Gamma Seed"]["kg_by_status"]["CONFIRMED"], "1.500")
        self.assertEqual(after["Alpha Seed"]["total_kg"], before["Alpha Seed"]["total_kg"])

    def _ids(self, response):
        return [row["public_id"] for row in response.data["results"]]

    # -- listing --------------------------------------------------------------

    def test_no_filter_returns_the_first_page_and_the_catalogues(self):
        """The page shape, the declared filters and sorts, and the card contents.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_no_filter_returns_the_first_page_and_the_catalogues
        """
        self._seed_orders()

        response = self.client.get(GET_ORDERS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 3)
        # Default sort is newest first.
        self.assertEqual(
            self._ids(response),
            [self.third.public_id, self.second.public_id, self.first.public_id],
        )
        self.assertEqual(
            [(f["filter"], f["kind"]) for f in response.data["available_filters"]],
            [
                ("public_id", "text"),
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
            row for row in response.data["results"] if row["public_id"] == self.third.public_id
        )
        self.assertEqual(card["client"]["company_name"], "Acme Seeds")
        self.assertEqual(card["city"]["name"], "Surat")
        self.assertEqual(card["status"], "BOOKED")
        self.assertEqual(card["dispatch_mode"], "PRIVATE")
        # Two lines: 2 alpha bags at 1000 plus 1 beta bag at 500; 2x10 + 1x5 packets.
        self.assertEqual(card["total_amount"], "2500.00")
        self.assertEqual(card["total_packets"], 25)
        self.assertEqual(card["item_count"], 2)
        self.assertEqual(
            sorted(p["product"]["name"] for p in card["packagings"]),
            ["Alpha Seed", "Beta Seed"],
        )

    def test_the_list_is_scoped_to_the_calling_sales_person(self):
        """Another sales person's order is neither listed nor advertised in the
        client catalogue, and naming their client finds nothing.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_the_list_is_scoped_to_the_calling_sales_person
        """
        self._seed_orders()

        response = self.client.get(GET_ORDERS_URL)

        self.assertNotIn(self.theirs.public_id, self._ids(response))
        clients = next(
            f for f in response.data["available_filters"] if f["filter"] == "client"
        )
        self.assertEqual(
            [o["label"] for o in clients["options"]], ["Acme Seeds", "Beta Seeds"]
        )

        # Naming the other sales person's client explicitly still returns nothing.
        theirs = self.client.get(GET_ORDERS_URL, {"client": self.rival.public_id})
        self.assertEqual(theirs.data["results"], [])
        self.assertEqual(theirs.data["total_count"], 0)
        self.assertEqual(Order.objects.count(), 4)

    # -- filtering ------------------------------------------------------------

    def test_filtering_by_client(self):
        """tests/android/test_orders.py::AndroidOrderListApiTest::test_filtering_by_client"""
        self._seed_orders()

        acme = self.client.get(GET_ORDERS_URL, {"client": self.acme.public_id})
        self.assertEqual(
            sorted(self._ids(acme)), sorted([self.first.public_id, self.third.public_id])
        )

        both = self.client.get(
            GET_ORDERS_URL,
            {"client": f"{self.acme.public_id},{self.beta.public_id}"},
        )
        self.assertEqual(both.data["total_count"], 3)

    def test_filtering_by_product(self):
        """An order matches when any of its lines names the product, and the card
        still reports the order's whole total -- not just the matching line.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_filtering_by_product
        """
        self._seed_orders()

        beta = self.client.get(GET_ORDERS_URL, {"product": self.beta_product.public_id})

        self.assertEqual(
            sorted(self._ids(beta)),
            sorted([self.second.public_id, self.third.public_id]),
        )
        mixed = next(
            row for row in beta.data["results"] if row["public_id"] == self.third.public_id
        )
        self.assertEqual(mixed["total_amount"], "2500.00")

        products = next(
            f for f in beta.data["available_filters"] if f["filter"] == "product"
        )
        self.assertEqual(
            [o["label"] for o in products["options"]], ["Alpha Seed", "Beta Seed"]
        )

    def test_filtering_by_city(self):
        """tests/android/test_orders.py::AndroidOrderListApiTest::test_filtering_by_city"""
        self._seed_orders()

        ahmedabad = self.client.get(GET_ORDERS_URL, {"city_id": str(self.other_city.id)})
        self.assertEqual(self._ids(ahmedabad), [self.second.public_id])

        cities = next(
            f for f in ahmedabad.data["available_filters"] if f["filter"] == "city_id"
        )
        self.assertEqual([o["label"] for o in cities["options"]], ["Ahmedabad", "Surat"])

    def test_filtering_by_status(self):
        """A declared code narrows the list; an undeclared one is a 400.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_filtering_by_status
        """
        self._seed_orders()

        on_hold = self.client.get(GET_ORDERS_URL, {"status": "ON_HOLD"})
        self.assertEqual(self._ids(on_hold), [self.second.public_id])

        booked = self.client.get(GET_ORDERS_URL, {"status": "BOOKED"})
        self.assertEqual(booked.data["total_count"], 2)

        unknown = self.client.get(GET_ORDERS_URL, {"status": "SHIPPED"})
        self.assertEqual(unknown.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown status", unknown.data["detail"])

    def test_filters_combine(self):
        """tests/android/test_orders.py::AndroidOrderListApiTest::test_filters_combine"""
        self._seed_orders()

        response = self.client.get(
            GET_ORDERS_URL,
            {"client": self.acme.public_id, "product": self.beta_product.public_id},
        )

        self.assertEqual(self._ids(response), [self.third.public_id])

    # -- sorting --------------------------------------------------------------

    def test_sorting_by_price_and_created_at(self):
        """``price`` orders on the order's total, in both directions.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_sorting_by_price_and_created_at
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
                response = self.client.get(GET_ORDERS_URL, query)
                self.assertEqual(self._ids(response), expected)

    def test_a_verified_order_reports_who_approved_it(self):
        """The approval fields are rendered as strings, not model instances.

        Every other order in this suite is unverified, so ``verified_by`` is
        null and any value that cannot be serialized stays hidden. Setting it
        here is what exercises the non-null path.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_a_verified_order_reports_who_approved_it
        """
        self._seed_orders()
        approver = User.objects.create_user(
            phone_number="9000000399",
            name="Sales Admin",
            is_verified=True,
            created_by=self.superuser,
            verified_by=self.superuser,
        )
        Admin.objects.create(user=approver, created_by=self.superuser)
        self.first.verified_by = approver
        self.first.verified_at = indian_now()
        self.first.save(update_fields=["verified_by", "verified_at", "updated_at"])

        response = self.client.get(GET_ORDERS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        card = next(
            row
            for row in response.data["results"]
            if row["public_id"] == self.first.public_id
        )
        self.assertEqual(card["verified_by"], "Sales Admin")
        self.assertIsNotNone(card["verified_at"])
        # BOOKED, not CONFIRMED -- ``verified`` tracks the status, not the stamp.
        self.assertFalse(card["verified"])

        other = next(
            row
            for row in response.data["results"]
            if row["public_id"] == self.second.public_id
        )
        self.assertIsNone(other["verified_by"])
        self.assertIsNone(other["verified_at"])

    def test_each_product_on_the_card_carries_its_picture(self):
        """The image comes off the prefetched product, blank when none is set.

        tests/android/test_orders.py::AndroidOrderListApiTest::test_each_product_on_the_card_carries_its_picture
        """
        self._seed_orders()

        response = self.client.get(GET_ORDERS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        card = next(
            row
            for row in response.data["results"]
            if row["public_id"] == self.third.public_id
        )
        images = {
            p["product"]["name"]: p["product"]["image_url"]
            for p in card["packagings"]
        }
        self.assertEqual(images["Alpha Seed"], "/media/products/alpha.jpg")
        # Beta Seed has no picture: an empty string, never null.
        self.assertEqual(images["Beta Seed"], "")
