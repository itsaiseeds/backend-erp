"""Sales-admin custom-order CRUD.

``POST /api/sales-admin/create-custom-order``,
``GET /api/sales-admin/custom-orders/``,
``GET|DELETE /api/sales-admin/custom-order/<public_id>``,
``PATCH /api/sales-admin/edit-custom-order/<public_id>``,
``POST /api/sales-admin/dispatch-custom-order/<public_id>`` and
``POST /api/sales-admin/revert-custom-order-dispatch/<public_id>`` -- plus the
custom-order rows of ``dispatch-challans/`` and ``export/dispatch-receipts``.

Every custom order here is booked by one sales admin and read, edited and
deleted by *another* -- the endpoints are not scoped to who booked the order.
Authentication and role gating are proven once in
``tests/test_view_contracts.py``; the loose-pool arithmetic in
``tests/test_custom_order_operations.py``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import create_client_with_details, verify_client
from aggregator.CustomOrderOperations import (
    attach_private_dispatch_details,
    create_custom_order,
    delete_custom_order,
    update_custom_order_status,
)
from aggregator.models import (
    City,
    Country,
    CustomOrder,
    CustomOrderItem,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import create_order, dispatch_order, verify_order
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.common import WebApiTestCase, book_raw_material_for_every_product

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
CREATE_URL = "/api/sales-admin/create-custom-order"
LIST_URL = "/api/sales-admin/custom-orders/"
DETAIL_URL = "/api/sales-admin/custom-order/{public_id}"
EDIT_URL = "/api/sales-admin/edit-custom-order/{public_id}"
DISPATCH_URL = "/api/sales-admin/dispatch-custom-order/{public_id}"
REVERT_URL = "/api/sales-admin/revert-custom-order-dispatch/{public_id}"
CHALLANS_URL = "/api/sales-admin/dispatch-challans/"
RECEIPTS_URL = "/api/sales-admin/export/dispatch-receipts"

W1 = Decimal("1.000")
W05 = Decimal("0.500")


class SalesAdminCustomOrderApiTest(WebApiTestCase):
    """Cover booking, listing, reading, editing and deleting custom orders.

    tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Two sales admins, a verified and an unverified client, two products."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.other_city = City.objects.get(name="Ahmedabad", state=cls.state)

        cls.admin_one = cls._admin("9000000601", "Admin One", counts_stock=True)
        cls.admin_two = cls._admin("9000000602", "Admin Two")

        cls.sales_person = User.objects.create_user(
            phone_number="9000000603",
            name="Sales One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(
            user=cls.sales_person, city=cls.city, created_by=cls.superuser
        )

        cls.acme = cls._client("Acme Seeds", "27AAPFU0939F1ZV")
        verify_client(cls.acme, cls.admin_one)
        cls.pending = cls._client("Pending Seeds", "27AAPFU0939F1ZB")

        cls.cotton = cls._product("Loose Cotton", Decimal("100.00"))
        cls.wheat = cls._product("Loose Wheat", Decimal("80.00"))
        # Loose counts are checked against raw material.
        book_raw_material_for_every_product(actor=cls.superuser)

    @classmethod
    def _admin(cls, phone, name, *, counts_stock=False):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=user, created_by=cls.superuser, can_update_stock_count=counts_stock
        )
        return user

    @classmethod
    def _client(cls, company_name, gst):
        """A client with two addresses: Surat (primary) and Ahmedabad."""
        return create_client_with_details(
            company_name=company_name,
            company_phone="9876543210",
            gst_number=gst,
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "line_2": "",
                    "pincode": "395007",
                    "city": cls.city,
                    "state": cls.state,
                    "country": cls.country,
                    "label": "Warehouse",
                    "is_primary": True,
                },
                {
                    "line_1": "2 CG Road",
                    "line_2": "",
                    "pincode": "380001",
                    "city": cls.other_city,
                    "state": cls.state,
                    "country": cls.country,
                    "label": "Branch",
                    "is_primary": False,
                },
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": f"{company_name} Transport"}],
            actor=cls.sales_person,
        )

    @classmethod
    def _product(cls, name, rate_per_kg):
        """A product packed at 1kg and 0.5kg -- two loose pools."""
        product = Product.objects.create(
            name=name,
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=rate_per_kg,
            created_by=cls.superuser,
        )
        for weight in (W1, W05):
            ProductPackaging.objects.create(
                product=product,
                packet_weight=weight,
                packets=10,
                selling_price=rate_per_kg * weight * 10,
                created_by=cls.superuser,
            )
        return product

    def setUp(self):
        super().setUp()
        self._count_loose(100)
        self.login_as(self.admin_two)

    # -- helpers --------------------------------------------------------------

    def _count_loose(self, packets):
        """Count ``packets`` loose packets in every pool of the two test products."""
        inv.record_loose_stocks(
            counts={
                (product, weight): packets
                for product in (self.cotton, self.wheat)
                for weight in (W1, W05)
            },
            actor=self.admin_one,
        )

    def _address_link(self, client, city):
        return client.client_addresses.get(address__city=city)

    def _book(self, lines, *, client=None, actor=None):
        """Book a custom order directly, as ``admin_one`` by default."""
        client = client or self.acme
        return create_custom_order(
            client=client,
            delivery_address=self._address_link(client, self.city).address,
            actor=actor or self.admin_one,
            items=[
                {"product": product, "packet_weight": weight, "packets": packets}
                for product, weight, packets in lines
            ],
        )

    def _line(self, product, weight, packets, price=None):
        line = {
            "product_public_id": product.public_id,
            "packet_weight": str(weight),
            "packets": packets,
        }
        if price is not None:
            line["negotiated_selling_price"] = price
        return line

    def _create(self, items, **overrides):
        body = {
            "client_public_id": self.acme.public_id,
            "client_address_id": self._address_link(self.acme, self.city).id,
            "items": items,
            **overrides,
        }
        return self.client.post(CREATE_URL, body, format="json")

    def _patch(self, order, body):
        return self.client.patch(
            EDIT_URL.format(public_id=order.public_id), body, format="json"
        )

    def _dispatch(self, order):
        attach_private_dispatch_details(
            order,
            dispatched_by=self.admin_one,
            dispatch_date=order.created_at.date(),
            from_city=self.city,
            to_city=self.city,
            driver_name="Ramesh Driver",
            driver_number="9876500009",
            vehicle_number="GJ05AB1234",
        )
        update_custom_order_status(order, StatusIds.DISPATCHED)

    # -- create ---------------------------------------------------------------

    def test_create_books_a_confirmed_order_that_reserves_packets(self):
        """Born CONFIRMED, verified by the booking admin, priced per packet weight.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_create_books_a_confirmed_order_that_reserves_packets
        """
        response = self._create(
            [
                self._line(self.cotton, W1, 10),
                self._line(self.cotton, W05, 4),
                self._line(self.wheat, W1, 2, price="75.00"),
            ],
            special_comments="Urgent",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["public_id"].startswith("CORD-"))
        self.assertEqual(response.data["status"], "CONFIRMED")
        self.assertEqual(response.data["special_comments"], "Urgent")
        self.assertEqual(response.data["client"]["public_id"], self.acme.public_id)
        prices = {
            (line["product"]["public_id"], line["packet_weight"]): line[
                "negotiated_selling_price"
            ]
            for line in response.data["items"]
        }
        self.assertEqual(
            prices,
            {
                (self.cotton.public_id, "1.000"): "100.00",
                (self.cotton.public_id, "0.500"): "50.00",
                (self.wheat.public_id, "1.000"): "75.00",
            },
        )
        self.assertEqual(response.data["total_packets"], 16)
        self.assertEqual(response.data["total_amount"], "1350.00")

        order = CustomOrder.objects.get(public_id=response.data["public_id"])
        self.assertEqual(order.created_by, self.admin_two)
        self.assertEqual(order.verified_by, self.admin_two)
        self.assertEqual(inv.reserved_loose_packets(self.cotton, W1), 10)
        self.assertEqual(inv.reserved_loose_packets(self.cotton, W05), 4)

    def test_create_refuses_an_unverified_client(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_create_refuses_an_unverified_client"""
        response = self._create(
            [self._line(self.cotton, W1, 1)],
            client_public_id=self.pending.public_id,
            client_address_id=self._address_link(self.pending, self.city).id,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.assertFalse(CustomOrder.objects.exists())

    def test_create_refuses_another_clients_address(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_create_refuses_another_clients_address"""
        response = self._create(
            [self._line(self.cotton, W1, 1)],
            client_address_id=self._address_link(self.pending, self.city).id,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_create_refuses_a_stock_shortfall(self):
        """The pool is 100 packets; 101 is refused and nothing is written.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_create_refuses_a_stock_shortfall
        """
        response = self._create(
            [self._line(self.cotton, W1, 101), self._line(self.wheat, W1, 1)]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomOrder.all_objects.exists())
        self.assertFalse(CustomOrderItem.all_objects.exists())

    def test_create_refuses_the_same_pool_twice(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_create_refuses_the_same_pool_twice"""
        response = self._create(
            [self._line(self.cotton, W1, 1), self._line(self.cotton, "1", 2)]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_create_refuses_a_deleted_product(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_create_refuses_a_deleted_product"""
        self.wheat.mark_deleted(self.superuser)

        response = self._create([self._line(self.wheat, W1, 1)])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(self.wheat.public_id, str(response.data))

    # -- list -----------------------------------------------------------------

    def test_list_shows_every_admins_custom_orders(self):
        """Admin Two sees Admin One's order too, and can narrow to either admin.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_list_shows_every_admins_custom_orders
        """
        mine = self._book([(self.wheat, W1, 1)], actor=self.admin_two)
        theirs = self._book([(self.cotton, W1, 2), (self.cotton, W05, 3)])

        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["total_count"], 2)
        by_id = {card["public_id"]: card for card in response.data["results"]}
        self.assertEqual(set(by_id), {mine.public_id, theirs.public_id})
        card = by_id[theirs.public_id]
        self.assertEqual(card["created_by"], "Admin One")
        self.assertEqual(card["verified_by"], "Admin One")
        self.assertEqual(card["client_created_by"], "Sales One")
        self.assertEqual(card["status"], "CONFIRMED")
        self.assertEqual(card["city"], {"id": self.city.id, "name": "Surat"})
        self.assertEqual(card["item_count"], 2)
        self.assertEqual(card["total_packets"], 5)
        self.assertEqual(card["total_amount"], "350.00")

        filters = {entry["filter"]: entry for entry in response.data["available_filters"]}
        self.assertEqual(
            {option["value"] for option in filters["created_by"]["options"]},
            {self.admin_one.id, self.admin_two.id},
        )

        response = self.client.get(LIST_URL, {"created_by": self.admin_one.id})
        self.assertEqual(
            [card["public_id"] for card in response.data["results"]], [theirs.public_id]
        )

    def test_list_filters_by_product_and_sorts_by_whole_order_price(self):
        """``?product=`` narrows the join, but ``price`` still sorts on the full total.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_list_filters_by_product_and_sorts_by_whole_order_price
        """
        # 1 x 100 + 10 x 80 = 900 in all, only 100 of it cotton.
        big = self._book([(self.cotton, W1, 1), (self.wheat, W1, 10)])
        small = self._book([(self.cotton, W1, 3)])  # 300
        self._book([(self.wheat, W05, 1)])  # no cotton

        response = self.client.get(
            LIST_URL, {"product": self.cotton.id, "sort": "price"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [card["public_id"] for card in response.data["results"]],
            [small.public_id, big.public_id],
        )

    def test_list_hides_deleted_custom_orders(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_list_hides_deleted_custom_orders"""
        order = self._book([(self.cotton, W1, 1)])
        delete_custom_order(order, self.admin_one)

        response = self.client.get(LIST_URL)

        self.assertEqual(response.data["total_count"], 0)

    # -- detail ---------------------------------------------------------------

    def test_detail_returns_the_order_with_the_full_client(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_detail_returns_the_order_with_the_full_client"""
        order = self._book([(self.cotton, W05, 6)])

        response = self.client.get(DETAIL_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["public_id"], order.public_id)
        self.assertEqual(len(response.data["client"]["addresses"]), 2)
        self.assertEqual(
            response.data["items"],
            [
                {
                    "product": {
                        "public_id": self.cotton.public_id,
                        "name": "Loose Cotton",
                    },
                    "packet_weight": "0.500",
                    "negotiated_selling_price": "50.00",
                    "packets": 6,
                    "line_total": "300.00",
                }
            ],
        )

    def test_detail_of_an_unknown_order_is_404(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_detail_of_an_unknown_order_is_404"""
        response = self.client.get(DETAIL_URL.format(public_id="CORD-NOPE"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- edit -----------------------------------------------------------------

    def test_another_admin_edits_address_dates_and_comments(self):
        """Comments append; client, status and audit keys are ignored.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_another_admin_edits_address_dates_and_comments
        """
        order = self._book([(self.cotton, W1, 1)])
        branch = self._address_link(self.acme, self.other_city)

        self._patch(order, {"special_comments": "First"})
        response = self._patch(
            order,
            {
                "client_address_id": branch.id,
                "expected_delivery_date": "2026-10-05",
                "special_comments": "Second",
                "status": "DELIVERED",
                "client_public_id": self.pending.public_id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["special_comments"], "First\nSecond")
        self.assertEqual(response.data["expected_delivery_date"], "2026-10-05")
        self.assertEqual(response.data["status"], "CONFIRMED")
        self.assertEqual(response.data["client"]["public_id"], self.acme.public_id)
        order.refresh_from_db()
        self.assertEqual(order.delivery_address_id, branch.address_id)
        self.assertEqual(order.created_by, self.admin_one)
        self.assertEqual(order.verified_by, self.admin_one)

    def test_edit_refuses_another_clients_address(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_edit_refuses_another_clients_address"""
        order = self._book([(self.cotton, W1, 1)])

        response = self._patch(
            order, {"client_address_id": self._address_link(self.pending, self.city).id}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_edit_replaces_the_lines_and_restores_a_removed_one(self):
        """A pool left out is removed; putting it back restores its original row.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_edit_replaces_the_lines_and_restores_a_removed_one
        """
        order = self._book([(self.cotton, W1, 5), (self.wheat, W1, 2)])
        wheat_row = order.items.get(product=self.wheat)

        response = self._patch(
            order,
            {
                "items": [
                    self._line(self.cotton, W1, 7, price="90.00"),
                    self._line(self.cotton, W05, 2),
                ]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            {
                (line["product"]["public_id"], line["packet_weight"], line["packets"])
                for line in response.data["items"]
            },
            {(self.cotton.public_id, "1.000", 7), (self.cotton.public_id, "0.500", 2)},
        )
        self.assertEqual(inv.reserved_loose_packets(self.wheat, W1), 0)
        self.assertEqual(inv.reserved_loose_packets(self.cotton, W1), 7)

        response = self._patch(
            order,
            {"items": [self._line(self.cotton, W1, 7), self._line(self.wheat, W1, 3)]},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        wheat_row.refresh_from_db()
        self.assertFalse(wheat_row.is_deleted)
        self.assertEqual(wheat_row.packets, 3)
        # The price sent on the earlier edit survives an edit that omits one.
        self.assertEqual(
            order.items.get(product=self.cotton, packet_weight=W1).negotiated_selling_price,
            Decimal("90.00"),
        )
        self.assertEqual(
            CustomOrderItem.all_objects.filter(custom_order=order).count(), 3
        )

    def test_edit_credits_the_packets_the_order_already_holds(self):
        """Holding 60 of a 100-packet pool, the order may grow to 100 but not 101.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_edit_credits_the_packets_the_order_already_holds
        """
        order = self._book([(self.cotton, W1, 60)])

        response = self._patch(order, {"items": [self._line(self.cotton, W1, 101)]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(order.items.get().packets, 60)

        response = self._patch(order, {"items": [self._line(self.cotton, W1, 100)]})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(inv.available_loose_packets(self.cotton, W1), 0)

    def test_edit_refuses_a_dispatched_order(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_edit_refuses_a_dispatched_order"""
        order = self._book([(self.cotton, W1, 1)])
        self._dispatch(order)

        response = self._patch(order, {"special_comments": "late"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_edit_refuses_an_empty_item_list(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_edit_refuses_an_empty_item_list"""
        order = self._book([(self.cotton, W1, 1)])

        response = self._patch(order, {"items": []})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(order.items.count(), 1)

    def test_edit_keeps_a_line_of_a_since_deleted_product(self):
        """A deleted product's existing line stays editable; a new weight of it does not.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_edit_keeps_a_line_of_a_since_deleted_product
        """
        order = self._book([(self.wheat, W1, 2)])
        self.wheat.mark_deleted(self.superuser)

        response = self._patch(order, {"items": [self._line(self.wheat, W1, 1)]})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        response = self._patch(
            order,
            {"items": [self._line(self.wheat, W1, 1), self._line(self.wheat, W05, 1)]},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- delete ---------------------------------------------------------------

    def test_another_admin_deletes_and_releases_the_packets(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_another_admin_deletes_and_releases_the_packets"""
        order = self._book([(self.cotton, W1, 40)])
        self.assertEqual(inv.available_loose_packets(self.cotton, W1), 60)

        response = self.client.delete(DETAIL_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(inv.available_loose_packets(self.cotton, W1), 100)
        deleted = CustomOrder.all_objects.get(pk=order.pk)
        self.assertTrue(deleted.is_deleted)
        self.assertEqual(deleted.status.code, "REJECTED")
        self.assertEqual(deleted.deleted_by, self.admin_two)
        self.assertFalse(CustomOrderItem.objects.filter(custom_order=order).exists())
        self.assertEqual(
            self.client.get(DETAIL_URL.format(public_id=order.public_id)).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_refuses_a_dispatched_order(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_delete_refuses_a_dispatched_order"""
        order = self._book([(self.cotton, W1, 1)])
        self._dispatch(order)

        response = self.client.delete(DETAIL_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomOrder.all_objects.get(pk=order.pk).is_deleted)

    # -- dispatch / revert ----------------------------------------------------

    def _dispatch_body(self, lots):
        return {
            "from_city_id": self.city.id,
            "driver_name": "Ramesh Driver",
            "driver_number": "9876500009",
            "vehicle_number": "GJ05AB1234",
            "items": [
                {
                    "product_public_id": product.public_id,
                    "packet_weight": str(weight),
                    "lot_number": lot,
                }
                for product, weight, lot in lots
            ],
        }

    def _post_dispatch(self, order, lots):
        return self.client.post(
            DISPATCH_URL.format(public_id=order.public_id),
            self._dispatch_body(lots),
            format="json",
        )

    def _challans(self, **params):
        """The challan list over a window wide enough to hold today."""
        now = indian_now()
        return self.client.get(
            CHALLANS_URL,
            {
                "start_date_time": (now - timedelta(days=1)).isoformat(),
                "end_date_time": (now + timedelta(days=1)).isoformat(),
                **params,
            },
        )

    def test_dispatch_goes_by_own_vehicle_and_writes_a_loose_challan(self):
        """Packets move from reserved to consumed; the challan lists at once, no LR.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_dispatch_goes_by_own_vehicle_and_writes_a_loose_challan
        """
        order = self._book([(self.cotton, W1, 10), (self.cotton, W05, 4)])

        response = self._post_dispatch(
            order, [(self.cotton, W1, "LOT-1KG"), (self.cotton, W05, "LOT-500G")]
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "DISPATCHED")
        order.refresh_from_db()
        self.assertIsNotNone(order.private_dispatch_details_id)
        self.assertIsNone(order.dispatch_details_id)
        self.assertEqual(order.private_dispatch_details.to_city, self.city)
        self.assertEqual(inv.reserved_loose_packets(self.cotton, W1), 0)
        self.assertEqual(inv.available_loose_packets(self.cotton, W1), 90)

        challans = self._challans()
        self.assertEqual(challans.status_code, status.HTTP_200_OK, challans.data)
        [row] = challans.data["results"]
        self.assertEqual(row["order_public_id"], order.public_id)
        self.assertEqual(row["order_type"], "CUSTOM_ORDER")
        self.assertTrue(row["dispatch"]["is_private"])
        self.assertEqual(row["dispatch"]["lr_number"], "")
        self.assertIsNone(row["dispatch"]["transport_agency"])
        self.assertEqual(row["receiver_details"]["company_name"], "Acme Seeds")
        self.assertEqual(
            sorted(row["items"], key=lambda line: line["packet_weight"]),
            [
                {
                    "product": {"public_id": self.cotton.public_id, "name": "Loose Cotton"},
                    "packet_weight": "0.500",
                    "packets": 4,
                    "lot_number": "LOT-500G",
                    "negotiated_selling_price": "50.00",
                    "line_total": "200.00",
                },
                {
                    "product": {"public_id": self.cotton.public_id, "name": "Loose Cotton"},
                    "packet_weight": "1.000",
                    "packets": 10,
                    "lot_number": "LOT-1KG",
                    "negotiated_selling_price": "100.00",
                    "line_total": "1000.00",
                },
            ],
        )
        self.assertEqual(row["total_packets"], 14)
        self.assertEqual(row["total_amount"], "1200.00")

    def test_dispatch_needs_a_lot_for_every_line(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_dispatch_needs_a_lot_for_every_line"""
        order = self._book([(self.cotton, W1, 1), (self.wheat, W1, 1)])

        response = self._post_dispatch(order, [(self.cotton, W1, "LOT-1")])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(self.wheat.public_id, str(response.data))
        order.refresh_from_db()
        self.assertEqual(order.status.code, "CONFIRMED")
        self.assertIsNone(order.private_dispatch_details_id)

    def test_a_dispatched_custom_order_cannot_be_dispatched_again(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_a_dispatched_custom_order_cannot_be_dispatched_again"""
        order = self._book([(self.cotton, W1, 1)])
        lots = [(self.cotton, W1, "LOT-1")]
        self.assertEqual(self._post_dispatch(order, lots).status_code, status.HTTP_200_OK)

        response = self._post_dispatch(order, lots)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revert_returns_to_confirmed_and_drops_the_challan(self):
        """Re-dispatching afterwards rewrites the same challan in place.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_revert_returns_to_confirmed_and_drops_the_challan
        """
        order = self._book([(self.cotton, W1, 5)])
        self._post_dispatch(order, [(self.cotton, W1, "LOT-A")])
        entry_id = CustomOrder.objects.get(pk=order.pk).dispatch_entry.public_id

        response = self.client.post(REVERT_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "CONFIRMED")
        self.assertEqual(inv.reserved_loose_packets(self.cotton, W1), 5)
        self.assertEqual(self._challans().data["total_count"], 0)

        # Reverted, the custom order is editable again -- and re-dispatchable.
        self.assertEqual(
            self._patch(order, {"items": [self._line(self.cotton, W1, 6)]}).status_code,
            status.HTTP_200_OK,
        )
        self._post_dispatch(order, [(self.cotton, W1, "LOT-B")])
        [row] = self._challans().data["results"]
        self.assertEqual(row["dispatch"]["public_id"], entry_id)
        self.assertEqual(row["items"][0]["lot_number"], "LOT-B")
        self.assertEqual(row["items"][0]["packets"], 6)

    def test_revert_refuses_an_undispatched_custom_order(self):
        """tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_revert_refuses_an_undispatched_custom_order"""
        order = self._book([(self.cotton, W1, 1)])

        response = self.client.post(REVERT_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- challans across both kinds -------------------------------------------

    def _dispatched_bag_order(self):
        """Book, verify and privately dispatch a normal bag order."""
        bag = ProductPackaging.objects.get(product=self.wheat, packet_weight=W1)
        order = create_order(
            client=self.acme,
            delivery_address=self._address_link(self.acme, self.city).address,
            actor=self.sales_person,
            items=[{"product_packaging": bag, "quantity": 2}],
        )
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), 400),
            actor=self.admin_one,
        )
        verify_order(order, self.admin_one)
        dispatch_order(
            order,
            actor=self.admin_one,
            from_city=self.city,
            driver_name="Ramesh Driver",
            driver_number="9876500009",
            vehicle_number="GJ05AB1234",
            lot_numbers={bag.public_id: "LOT-BAG"},
        )
        return order

    def test_the_challan_list_and_receipts_hold_both_kinds(self):
        """One page, one sort: an order row keeps its shape, a custom row is typed.

        tests/test_admin_custom_order_api.py::SalesAdminCustomOrderApiTest::test_the_challan_list_and_receipts_hold_both_kinds
        """
        bag_order = self._dispatched_bag_order()
        custom = self._book([(self.cotton, W1, 3)])
        self._post_dispatch(custom, [(self.cotton, W1, "LOT-C")])

        response = self._challans()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["total_count"], 2)
        # Newest dispatch first: the custom order left second.
        custom_row, order_row = response.data["results"]
        self.assertEqual(custom_row["order_public_id"], custom.public_id)
        self.assertEqual(order_row["order_public_id"], bag_order.public_id)
        self.assertNotIn("order_type", order_row)
        self.assertEqual(order_row["items"][0]["lot_number"], "LOT-BAG")
        self.assertEqual(order_row["items"][0]["quantity"], 2)

        response = self._challans(sort="created_at")
        self.assertEqual(
            [row["order_public_id"] for row in response.data["results"]],
            [bag_order.public_id, custom.public_id],
        )

        today = indian_now().date().isoformat()
        receipts = self.client.get(RECEIPTS_URL, {"start_date": today, "end_date": today})
        self.assertEqual(receipts.status_code, status.HTTP_200_OK, receipts.data)
        by_id = {row["order_public_id"]: row for row in receipts.data["results"]}
        self.assertEqual(set(by_id), {bag_order.public_id, custom.public_id})
        self.assertEqual(by_id[custom.public_id]["order_type"], "CUSTOM_ORDER")
        self.assertEqual(
            by_id[custom.public_id]["city"], {"id": self.city.id, "name": "Surat"}
        )
