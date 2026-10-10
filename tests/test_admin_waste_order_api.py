"""Sales-admin waste orders.

``POST /api/sales-admin/create-waste-order``,
``GET /api/sales-admin/waste-orders/``,
``PATCH /api/sales-admin/edit-waste-order/<public_id>`` and
``POST /api/sales-admin/dispatch-waste-order/<public_id>`` -- plus the shared
``custom-order/<public_id>`` (GET / DELETE) and
``revert-custom-order-dispatch/<public_id>`` a waste order reuses, and the waste
rows (``raw-material-waste/<public_id>``) it must not let anyone take away.

A waste order is a custom order with ``made_from_waste`` true: kilograms drawn
from a product's unused waste, never from raw stock or the loose packet pools.
Authentication and role gating are proven once in
``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import create_client_with_details, verify_client
from aggregator.CustomOrderOperations import create_custom_order
from aggregator.models import (
    City,
    Country,
    CustomOrder,
    CustomOrderItem,
    DispatchEntryItem,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.common import WebApiTestCase, book_raw_material_for_every_product

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
CREATE_URL = "/api/sales-admin/create-waste-order"
LIST_URL = "/api/sales-admin/waste-orders/"
CUSTOM_LIST_URL = "/api/sales-admin/custom-orders/"
DETAIL_URL = "/api/sales-admin/custom-order/{public_id}"
EDIT_URL = "/api/sales-admin/edit-waste-order/{public_id}"
EDIT_CUSTOM_URL = "/api/sales-admin/edit-custom-order/{public_id}"
DISPATCH_URL = "/api/sales-admin/dispatch-waste-order/{public_id}"
DISPATCH_CUSTOM_URL = "/api/sales-admin/dispatch-custom-order/{public_id}"
REVERT_URL = "/api/sales-admin/revert-custom-order-dispatch/{public_id}"
CHALLANS_URL = "/api/sales-admin/dispatch-challans/"
EXPORT_URL = "/api/sales-admin/export/custom-orders"
WASTE_URL = "/api/sales-admin/raw-material-waste/{public_id}"

W1 = Decimal("1.000")


class SalesAdminWasteOrderApiTest(WebApiTestCase):
    """Waste orders: the waste pool gate, the lifecycle and the guards around it.

    tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Two sales admins, a verified client and three products (two with waste)."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)

        cls.admin_one = cls._admin("9000000701", "Admin One")
        cls.admin_two = cls._admin("9000000702", "Admin Two")

        cls.sales_person = User.objects.create_user(
            phone_number="9000000703",
            name="Sales One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(
            user=cls.sales_person, city=cls.city, created_by=cls.superuser
        )

        cls.acme = create_client_with_details(
            company_name="Acme Seeds",
            company_phone="9876543210",
            gst_number="27AAPFU0939F1ZV",
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
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": "Acme Transport"}],
            actor=cls.sales_person,
        )
        verify_client(cls.acme, cls.admin_one)

        cls.cotton = cls._product("Waste Cotton", Decimal("100.00"))
        cls.wheat = cls._product("Waste Wheat", Decimal("80.00"))
        cls.maize = cls._product("Waste Maize", Decimal("60.00"))  # never has waste
        book_raw_material_for_every_product(actor=cls.superuser)

    @classmethod
    def _admin(cls, phone, name):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=user, created_by=cls.superuser, can_update_stock_count=True
        )
        return user

    @classmethod
    def _product(cls, name, rate_per_kg):
        product = Product.objects.create(
            name=name,
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=rate_per_kg,
            created_by=cls.superuser,
        )
        ProductPackaging.objects.create(
            product=product,
            packet_weight=W1,
            packets=10,
            selling_price=rate_per_kg * 10,
            created_by=cls.superuser,
        )
        return product

    def setUp(self):
        super().setUp()
        self.cotton_waste = inv.record_raw_waste(
            product=self.cotton,
            quantity_kg=Decimal("50"),
            reason="rain",
            actor=self.admin_one,
        )
        self.wheat_waste = inv.record_raw_waste(
            product=self.wheat,
            quantity_kg=Decimal("20"),
            reason="rats",
            actor=self.admin_one,
        )
        self.login_as(self.admin_two)

    # -- helpers --------------------------------------------------------------

    def _address_id(self):
        return self.acme.client_addresses.get(address__city=self.city).id

    def _line(self, product, kg, price="40.00"):
        line = {"product_public_id": product.public_id, "quantity_kg": str(kg)}
        if price is not None:
            line["negotiated_selling_price"] = price
        return line

    def _create(self, items, **overrides):
        body = {
            "client_public_id": self.acme.public_id,
            "client_address_id": self._address_id(),
            "items": items,
            **overrides,
        }
        return self.client.post(CREATE_URL, body, format="json")

    def _book(self, *lines):
        """Book a waste order through the API and return the model row."""
        response = self._create([self._line(p, kg) for p, kg in lines])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return CustomOrder.objects.get(public_id=response.data["public_id"])

    def _dispatch_body(self, **overrides):
        return {
            "from_city_id": self.city.id,
            "driver_name": "Ramesh Driver",
            "driver_number": "9876500009",
            "vehicle_number": "GJ05AB1234",
            **overrides,
        }

    def _dispatch(self, order, **overrides):
        return self.client.post(
            DISPATCH_URL.format(public_id=order.public_id),
            self._dispatch_body(**overrides),
            format="json",
        )

    def _patch(self, order, body):
        return self.client.patch(
            EDIT_URL.format(public_id=order.public_id), body, format="json"
        )

    def _book_packet_order(self):
        """A normal (packet) custom order, for the cross-kind guards."""
        inv.record_loose_stocks(counts={(self.cotton, W1): 10}, actor=self.admin_one)
        return create_custom_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.get(
                address__city=self.city
            ).address,
            actor=self.admin_one,
            items=[{"product": self.cotton, "packet_weight": W1, "packets": 2}],
        )

    # -- create ---------------------------------------------------------------

    def test_create_books_a_confirmed_kg_order_that_reserves_waste(self):
        """Born CONFIRMED, kg lines at a per-kg price, waste reserved, raw untouched.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_create_books_a_confirmed_kg_order_that_reserves_waste
        """
        raw_before = inv.raw_available_kg(self.cotton)

        response = self._create(
            [self._line(self.cotton, "30.5", "40.00"), self._line(self.wheat, "5", "10.50")],
            special_comments="Cattle feed",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["public_id"].startswith("CORD-"))
        self.assertEqual(response.data["status"], "CONFIRMED")
        self.assertTrue(response.data["made_from_waste"])
        self.assertEqual(response.data["unit_of_measure"], "kg")
        self.assertEqual(response.data["total_kg"], "35.500")
        self.assertEqual(response.data["total_packets"], 0)
        self.assertEqual(response.data["total_amount"], "1272.50")
        lines = {
            line["product"]["public_id"]: line for line in response.data["items"]
        }
        cotton_line = lines[self.cotton.public_id]
        self.assertEqual(cotton_line["quantity_kg"], "30.500")
        self.assertIsNone(cotton_line["packets"])
        self.assertIsNone(cotton_line["packet_weight"])
        self.assertEqual(cotton_line["negotiated_selling_price"], "40.00")
        self.assertEqual(cotton_line["line_total"], "1220.00")

        order = CustomOrder.objects.get(public_id=response.data["public_id"])
        self.assertTrue(order.made_from_waste)
        self.assertEqual(order.unit_of_measure, "kg")
        self.assertEqual(order.created_by, self.admin_two)
        self.assertEqual(order.verified_by, self.admin_two)
        # The waste pool is reserved; raw stock and the loose pools are not.
        self.assertEqual(inv.waste_reserved_kg(self.cotton), Decimal("30.500"))
        self.assertEqual(inv.waste_available_kg(self.cotton), Decimal("19.500"))
        self.assertEqual(inv.waste_available_kg(self.wheat), Decimal("15.000"))
        self.assertEqual(inv.raw_available_kg(self.cotton), raw_before)
        self.assertEqual(inv.reserved_loose_packets(self.cotton, W1), 0)

    def test_create_refuses_more_than_the_unused_waste(self):
        """Cotton has 50 kg of waste: 50.001 is refused and nothing is written.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_create_refuses_more_than_the_unused_waste
        """
        response = self._create(
            [self._line(self.cotton, "50.001"), self._line(self.wheat, "1")]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Waste Cotton", str(response.data))
        self.assertFalse(CustomOrder.all_objects.exists())
        self.assertFalse(CustomOrderItem.all_objects.exists())

    def test_create_allows_exactly_the_unused_waste(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_create_allows_exactly_the_unused_waste"""
        self._book((self.cotton, "50"))

        self.assertEqual(inv.waste_available_kg(self.cotton), Decimal("0.000"))

    def test_a_second_order_cannot_spend_the_waste_the_first_holds(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_a_second_order_cannot_spend_the_waste_the_first_holds"""
        self._book((self.cotton, "30"))

        response = self._create([self._line(self.cotton, "21")])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CustomOrder.objects.count(), 1)
        self.assertEqual(self._create([self._line(self.cotton, "20")]).status_code, 201)

    def test_create_refuses_a_product_with_no_waste(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_create_refuses_a_product_with_no_waste"""
        response = self._create([self._line(self.maize, "1")])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomOrder.all_objects.exists())

    def test_create_requires_a_price_per_kg(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_create_requires_a_price_per_kg"""
        response = self._create([self._line(self.cotton, "1", price=None)])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("negotiated_selling_price", str(response.data))
        self.assertFalse(CustomOrder.all_objects.exists())

    def test_create_refuses_the_same_product_twice(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_create_refuses_the_same_product_twice"""
        response = self._create(
            [self._line(self.cotton, "1"), self._line(self.cotton, "2")]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomOrder.all_objects.exists())

    def test_create_refuses_packet_style_lines(self):
        """A packet line (no quantity_kg) is not a waste line.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_create_refuses_packet_style_lines
        """
        response = self._create(
            [
                {
                    "product_public_id": self.cotton.public_id,
                    "packet_weight": "1.000",
                    "packets": 5,
                    "negotiated_selling_price": "40.00",
                }
            ]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomOrder.all_objects.exists())

    # -- dispatch / revert / delete -------------------------------------------

    def test_dispatch_consumes_the_waste_and_writes_a_kg_challan(self):
        """No lot numbers needed; the challan carries kg lines with a blank lot.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_dispatch_consumes_the_waste_and_writes_a_kg_challan
        """
        order = self._book((self.cotton, "30"), (self.wheat, "5"))
        raw_before = inv.raw_available_kg(self.cotton)

        response = self._dispatch(order)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "DISPATCHED")
        self.assertEqual(inv.waste_reserved_kg(self.cotton), Decimal("0"))
        self.assertEqual(inv.waste_consumed_kg(self.cotton), Decimal("30.000"))
        self.assertEqual(inv.waste_available_kg(self.cotton), Decimal("20.000"))
        self.assertEqual(inv.raw_available_kg(self.cotton), raw_before)

        lines = DispatchEntryItem.objects.filter(
            dispatch_entry__custom_order=order
        ).order_by("product__name")
        self.assertEqual(
            [(line.quantity_kg, line.quantity, line.lot_number) for line in lines],
            [(Decimal("30.000"), None, ""), (Decimal("5.000"), None, "")],
        )

        now = indian_now()
        challans = self.client.get(
            CHALLANS_URL,
            {
                "start_date_time": (now - timedelta(days=1)).isoformat(),
                "end_date_time": (now + timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(challans.status_code, status.HTTP_200_OK, challans.data)
        (row,) = [
            r for r in challans.data["results"] if r["order_public_id"] == order.public_id
        ]
        self.assertEqual(row["order_type"], "WASTE_ORDER")
        self.assertEqual(row["unit_of_measure"], "kg")
        self.assertEqual(row["total_kg"], "35.000")
        self.assertIsNone(row["items"][0]["packets"])
        self.assertIsNone(row["items"][0]["packet_weight"])

    def test_dispatch_records_optional_lot_numbers(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_dispatch_records_optional_lot_numbers"""
        order = self._book((self.cotton, "30"), (self.wheat, "5"))

        response = self._dispatch(
            order,
            items=[{"product_public_id": self.cotton.public_id, "lot_number": "LOT-9"}],
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        lots = dict(
            DispatchEntryItem.objects.filter(
                dispatch_entry__custom_order=order
            ).values_list("product__name", "lot_number")
        )
        self.assertEqual(lots, {"Waste Cotton": "LOT-9", "Waste Wheat": ""})

    def test_dispatch_refuses_a_lot_for_a_product_not_on_the_order(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_dispatch_refuses_a_lot_for_a_product_not_on_the_order"""
        order = self._book((self.cotton, "30"))

        response = self._dispatch(
            order,
            items=[{"product_public_id": self.wheat.public_id, "lot_number": "LOT-9"}],
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status.code, "CONFIRMED")

    def test_dispatch_requires_the_driver_and_vehicle(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_dispatch_requires_the_driver_and_vehicle"""
        order = self._book((self.cotton, "30"))

        for field in ("driver_name", "driver_number", "vehicle_number"):
            with self.subTest(field=field):
                body = self._dispatch_body()
                del body[field]
                response = self.client.post(
                    DISPATCH_URL.format(public_id=order.public_id), body, format="json"
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_dispatched_waste_order_cannot_be_dispatched_again(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_a_dispatched_waste_order_cannot_be_dispatched_again"""
        order = self._book((self.cotton, "30"))
        self.assertEqual(self._dispatch(order).status_code, status.HTTP_200_OK)

        self.assertEqual(self._dispatch(order).status_code, status.HTTP_400_BAD_REQUEST)

    def test_reverting_a_dispatch_reserves_the_waste_again(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_reverting_a_dispatch_reserves_the_waste_again"""
        order = self._book((self.cotton, "30"))
        self._dispatch(order)

        response = self.client.post(REVERT_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "CONFIRMED")
        self.assertEqual(inv.waste_reserved_kg(self.cotton), Decimal("30.000"))
        self.assertEqual(inv.waste_consumed_kg(self.cotton), Decimal("0"))
        # ... and it can be dispatched again, rewriting the same challan.
        self.assertEqual(self._dispatch(order).status_code, status.HTTP_200_OK)
        self.assertEqual(
            DispatchEntryItem.objects.filter(dispatch_entry__custom_order=order).count(),
            1,
        )

    def test_deleting_a_confirmed_waste_order_returns_the_waste(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_deleting_a_confirmed_waste_order_returns_the_waste"""
        order = self._book((self.cotton, "30"))

        response = self.client.delete(DETAIL_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(inv.waste_available_kg(self.cotton), Decimal("50.000"))
        self.assertTrue(CustomOrder.all_objects.get(pk=order.pk).is_deleted)

    def test_a_dispatched_waste_order_cannot_be_deleted(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_a_dispatched_waste_order_cannot_be_deleted"""
        order = self._book((self.cotton, "30"))
        self._dispatch(order)

        response = self.client.delete(DETAIL_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(inv.waste_consumed_kg(self.cotton), Decimal("30.000"))

    def test_detail_reads_a_waste_order(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_detail_reads_a_waste_order"""
        order = self._book((self.cotton, "30"))

        response = self.client.get(DETAIL_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["made_from_waste"])
        self.assertEqual(response.data["total_kg"], "30.000")

    # -- edit -----------------------------------------------------------------

    def test_edit_replaces_the_lines_and_rechecks_the_waste(self):
        """Raising a line is covered by the waste net of what the order holds.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_edit_replaces_the_lines_and_rechecks_the_waste
        """
        order = self._book((self.cotton, "30"))

        # 30 held + 20 free = 50: exactly enough.
        response = self._patch(
            order, {"items": [{"product_public_id": self.cotton.public_id, "quantity_kg": "50"}]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["total_kg"], "50.000")
        # The price was omitted, so the existing one stays.
        self.assertEqual(response.data["items"][0]["negotiated_selling_price"], "40.00")
        self.assertEqual(inv.waste_available_kg(self.cotton), Decimal("0.000"))

        over = self._patch(
            order, {"items": [{"product_public_id": self.cotton.public_id, "quantity_kg": "50.5"}]}
        )
        self.assertEqual(over.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            CustomOrderItem.objects.get(custom_order=order).quantity_kg, Decimal("50.000")
        )

    def test_edit_can_shrink_and_swap_lines(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_edit_can_shrink_and_swap_lines"""
        order = self._book((self.cotton, "30"))

        response = self._patch(
            order,
            {"items": [self._line(self.wheat, "4", price="12.00")]},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual([i["product"]["public_id"] for i in response.data["items"]], [self.wheat.public_id])
        self.assertEqual(inv.waste_available_kg(self.cotton), Decimal("50.000"))
        self.assertEqual(inv.waste_available_kg(self.wheat), Decimal("16.000"))

    def test_edit_needs_a_price_on_a_new_line(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_edit_needs_a_price_on_a_new_line"""
        order = self._book((self.cotton, "30"))

        response = self._patch(
            order,
            {
                "items": [
                    self._line(self.cotton, "30", price=None),
                    self._line(self.wheat, "4", price=None),
                ]
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CustomOrderItem.objects.filter(custom_order=order).count(), 1)

    def test_a_dispatched_waste_order_cannot_be_edited(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_a_dispatched_waste_order_cannot_be_edited"""
        order = self._book((self.cotton, "30"))
        self._dispatch(order)

        response = self._patch(order, {"special_comments": "late"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- the two kinds stay apart ---------------------------------------------

    def test_the_packet_verbs_refuse_a_waste_order(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_the_packet_verbs_refuse_a_waste_order"""
        order = self._book((self.cotton, "30"))

        edit = self.client.patch(
            EDIT_CUSTOM_URL.format(public_id=order.public_id),
            {"special_comments": "x"},
            format="json",
        )
        dispatch = self.client.post(
            DISPATCH_CUSTOM_URL.format(public_id=order.public_id),
            {
                **self._dispatch_body(),
                "items": [
                    {
                        "product_public_id": self.cotton.public_id,
                        "packet_weight": "1.000",
                        "lot_number": "L",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(edit.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(dispatch.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.status.code, "CONFIRMED")

    def test_the_waste_verbs_refuse_a_packet_order(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_the_waste_verbs_refuse_a_packet_order"""
        packet_order = self._book_packet_order()

        edit = self._patch(packet_order, {"special_comments": "x"})
        dispatch = self._dispatch(packet_order)

        self.assertEqual(edit.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(dispatch.status_code, status.HTTP_400_BAD_REQUEST)

    def test_waste_orders_stay_out_of_the_packet_pools(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_waste_orders_stay_out_of_the_packet_pools"""
        packet_order = self._book_packet_order()
        self._book((self.cotton, "30"))

        self.assertEqual(inv.reserved_loose_packets(self.cotton, W1), 2)
        self.assertEqual(inv.available_loose_packets(self.cotton, W1), 8)
        self.assertEqual(packet_order.items.get().packets, 2)

    # -- lists / export -------------------------------------------------------

    def test_the_lists_and_export_keep_the_two_kinds_apart(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_the_lists_and_export_keep_the_two_kinds_apart"""
        packet_order = self._book_packet_order()
        waste_order = self._book((self.cotton, "30"))

        waste_list = self.client.get(LIST_URL)
        custom_list = self.client.get(CUSTOM_LIST_URL)

        self.assertEqual(waste_list.status_code, status.HTTP_200_OK, waste_list.data)
        self.assertEqual(
            [o["public_id"] for o in waste_list.data["results"]], [waste_order.public_id]
        )
        card = waste_list.data["results"][0]
        self.assertTrue(card["made_from_waste"])
        self.assertEqual(card["total_kg"], "30.000")
        self.assertEqual(card["items"][0]["quantity_kg"], "30.000")
        self.assertEqual(
            [o["public_id"] for o in custom_list.data["results"]], [packet_order.public_id]
        )
        self.assertFalse(custom_list.data["results"][0]["made_from_waste"])

        today = indian_now().date()
        exported = self.client.get(
            EXPORT_URL,
            {"start_date": today.isoformat(), "end_date": today.isoformat()},
        )
        self.assertEqual(exported.status_code, status.HTTP_200_OK, exported.data)
        self.assertEqual(
            [o["public_id"] for o in exported.data["results"]], [packet_order.public_id]
        )

    def test_the_waste_list_sorts_by_price(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_the_waste_list_sorts_by_price"""
        cheap = self._book((self.wheat, "1"))  # 1 kg x 40.00
        dear = self._book((self.cotton, "30"))  # 30 kg x 40.00

        response = self.client.get(LIST_URL, {"sort": "-price"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [o["public_id"] for o in response.data["results"]],
            [dear.public_id, cheap.public_id],
        )

    # -- the waste rows a waste order depends on ------------------------------

    def test_waste_held_by_an_order_cannot_be_lowered_or_deleted(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_waste_held_by_an_order_cannot_be_lowered_or_deleted"""
        self._book((self.cotton, "30"))
        url = WASTE_URL.format(public_id=self.cotton_waste.public_id)

        lowered = self.client.patch(url, {"quantity_kg": "29.999"}, format="json")
        deleted = self.client.delete(url)
        ok = self.client.patch(url, {"quantity_kg": "30"}, format="json")

        self.assertEqual(lowered.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(deleted.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ok.status_code, status.HTTP_200_OK, ok.data)
        self.assertEqual(inv.waste_available_kg(self.cotton), Decimal("0.000"))

    def test_waste_can_be_removed_once_the_order_is_withdrawn(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_waste_can_be_removed_once_the_order_is_withdrawn"""
        order = self._book((self.cotton, "30"))
        self.client.delete(DETAIL_URL.format(public_id=order.public_id))

        response = self.client.delete(WASTE_URL.format(public_id=self.cotton_waste.public_id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(inv.waste_available_kg(self.cotton), Decimal("0.000"))

    def test_raising_waste_makes_more_available(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_raising_waste_makes_more_available"""
        self._book((self.cotton, "50"))
        self.client.patch(
            WASTE_URL.format(public_id=self.cotton_waste.public_id),
            {"quantity_kg": "70"},
            format="json",
        )

        self.assertEqual(self._create([self._line(self.cotton, "20")]).status_code, 201)

    # -- who may touch waste orders -------------------------------------------

    def test_only_a_sales_admin_can_use_the_waste_order_endpoints(self):
        """A salesperson or an anonymous caller is refused on every verb; nothing is written.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_only_a_sales_admin_can_use_the_waste_order_endpoints
        """
        order = self._book((self.cotton, "30"))
        refused = (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        create_body = {
            "client_public_id": self.acme.public_id,
            "client_address_id": self._address_id(),
            "items": [self._line(self.wheat, "5")],
        }

        for who, login in (
            ("salesperson", lambda: self.login_as(self.sales_person)),
            ("anonymous", self.clear_auth),
        ):
            login()
            with self.subTest(who=who):
                responses = {
                    "create": self.client.post(CREATE_URL, create_body, format="json"),
                    "list": self.client.get(LIST_URL),
                    "edit": self._patch(order, {"special_comments": "x"}),
                    "dispatch": self._dispatch(order),
                    "delete": self.client.delete(DETAIL_URL.format(public_id=order.public_id)),
                }
                for verb, response in responses.items():
                    self.assertIn(
                        response.status_code, refused, f"{who} {verb}: {response.status_code}"
                    )

        order.refresh_from_db()
        self.assertEqual(order.status.code, "CONFIRMED")
        self.assertFalse(order.is_deleted)
        self.assertEqual(CustomOrder.objects.count(), 1)

    # -- raw-material-stock shows the waste pool -------------------------------

    def test_raw_material_stock_reports_the_waste_pool(self):
        """waste_* follow the order's life; available_kg (raw) never moves.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_raw_material_stock_reports_the_waste_pool
        """

        def line():
            response = self.client.get(
                "/api/sales-admin/raw-material-stock", {"product": self.cotton.public_id}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            return response.data["lines"][0]

        before = line()
        self.assertEqual(before["wasted_kg"], "50.000")
        self.assertEqual(
            (before["waste_reserved_kg"], before["waste_consumed_kg"], before["waste_available_kg"]),
            ("0.000", "0.000", "50.000"),
        )

        order = self._book((self.cotton, "30"))
        booked = line()
        self.assertEqual(
            (booked["waste_reserved_kg"], booked["waste_consumed_kg"], booked["waste_available_kg"]),
            ("30.000", "0.000", "20.000"),
        )

        self._dispatch(order)
        dispatched = line()
        self.assertEqual(
            (dispatched["waste_reserved_kg"], dispatched["waste_consumed_kg"], dispatched["waste_available_kg"]),
            ("0.000", "30.000", "20.000"),
        )
        for key in ("incoming_kg", "packed_kg", "wasted_kg", "available_kg"):
            self.assertEqual(dispatched[key], before[key], key)

    # -- HSN code: free text, waste orders only ---------------------------------

    def test_hsn_code_is_optional_free_text_on_a_waste_order(self):
        """Blank by default; set on create, shown in detail and list, edited and cleared on edit.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_hsn_code_is_optional_free_text_on_a_waste_order
        """
        plain = self._book((self.wheat, "1"))
        self.assertEqual(plain.hsn_code, "")

        created = self._create([self._line(self.cotton, "5")], hsn_code="  1209 10 00 (waste)  ")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(created.data["hsn_code"], "1209 10 00 (waste)")
        order_id = created.data["public_id"]

        detail = self.client.get(DETAIL_URL.format(public_id=order_id))
        self.assertEqual(detail.data["hsn_code"], "1209 10 00 (waste)")
        listed = self.client.get(LIST_URL, {"public_id": order_id})
        self.assertEqual(listed.data["results"][0]["hsn_code"], "1209 10 00 (waste)")

        order = CustomOrder.objects.get(public_id=order_id)
        edited = self._patch(order, {"hsn_code": "23099010"})
        self.assertEqual(edited.status_code, status.HTTP_200_OK, edited.data)
        self.assertEqual(edited.data["hsn_code"], "23099010")
        # An edit that does not send it leaves it alone; an empty string clears it.
        self.assertEqual(self._patch(order, {"special_comments": "x"}).data["hsn_code"], "23099010")
        self.assertEqual(self._patch(order, {"hsn_code": ""}).data["hsn_code"], "")

    def test_hsn_code_is_limited_to_32_characters(self):
        """tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_hsn_code_is_limited_to_32_characters"""
        response = self._create([self._line(self.cotton, "5")], hsn_code="9" * 33)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomOrder.all_objects.exists())

    def test_only_a_waste_order_has_an_hsn_code(self):
        """A packet custom order never shows, takes or stores an HSN code.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_only_a_waste_order_has_an_hsn_code
        """
        waste = self._book((self.cotton, "5"))
        packet_order = self._book_packet_order()

        # Waste order: the key is always there (blank when not given).
        self.assertEqual(
            self.client.get(DETAIL_URL.format(public_id=waste.public_id)).data["hsn_code"], ""
        )
        # Packet order: no key in the detail, the list card or the edit response.
        detail = self.client.get(DETAIL_URL.format(public_id=packet_order.public_id))
        self.assertNotIn("hsn_code", detail.data)
        listed = self.client.get(CUSTOM_LIST_URL, {"public_id": packet_order.public_id})
        self.assertNotIn("hsn_code", listed.data["results"][0])
        patched = self.client.patch(
            EDIT_CUSTOM_URL.format(public_id=packet_order.public_id),
            {"hsn_code": "1209"},
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.data)
        self.assertNotIn("hsn_code", patched.data)
        packet_order.refresh_from_db()
        self.assertEqual(packet_order.hsn_code, "")

    def test_the_database_refuses_an_hsn_code_on_a_packet_order(self):
        """Even code that bypasses the API cannot put an HSN code on a packet order.

        tests/test_admin_waste_order_api.py::SalesAdminWasteOrderApiTest::test_the_database_refuses_an_hsn_code_on_a_packet_order
        """
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError, transaction

        packet_order = self._book_packet_order()
        packet_order.hsn_code = "1209"

        with self.assertRaises(ValidationError):  # model rule
            packet_order.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():  # database rule
            CustomOrder.objects.filter(pk=packet_order.pk).update(hsn_code="1209")
