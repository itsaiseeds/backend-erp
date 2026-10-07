"""``booked_for`` (client child orgs) across the order endpoints.

Booking (Android bag order, admin custom order), editing (admin order and
custom order), the two child pickers, and the challan / export / list payloads.
The get-or-create rules themselves live in
``tests/test_client_child_org_operations.py``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import create_client_with_details, verify_client
from aggregator.CustomOrderOperations import create_custom_order
from aggregator.models import (
    City,
    ClientChildOrg,
    Country,
    CustomOrder,
    Order,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.OrderOperations import create_order
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.common import DMLTestCase, book_raw_material_for_every_product

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
W1 = Decimal("1.000")

ANDROID_CREATE = "/android/api/v1/create-multi-select-bag-order"
ANDROID_ORDERS = "/android/api/v1/get-orders"
ANDROID_CHILDREN = "/android/api/v1/utilities/client-children"
ANDROID_CHALLANS = "/android/api/v1/get-challans"
ANDROID_CHALLAN = "/android/api/v1/get-challan/{public_id}"
WEB_CHILDREN = "/api/utilities/client-children"
CREATE_CUSTOM = "/api/sales-admin/create-custom-order"
EDIT_ORDER = "/api/sales-admin/edit-order/{public_id}"
EDIT_CUSTOM = "/api/sales-admin/edit-custom-order/{public_id}"
ORDER_DETAIL = "/api/sales-admin/order/{public_id}"
CUSTOM_DETAIL = "/api/sales-admin/custom-order/{public_id}"
ORDERS = "/api/sales-admin/orders/"
CUSTOM_ORDERS = "/api/sales-admin/custom-orders/"
VERIFY = "/api/sales-admin/verify-order/{public_id}"
DISPATCH = "/api/sales-admin/dispatch-order/{public_id}"
CHALLANS = "/api/sales-admin/dispatch-challans/"
RECEIPTS = "/api/sales-admin/export/dispatch-receipts"
EXPORT_ORDERS = "/api/sales-admin/export/orders"
EXPORT_CUSTOM = "/api/sales-admin/export/custom-orders"


class BookedForApiTest(DMLTestCase):
    """tests/test_booked_for_api.py::BookedForApiTest"""

    # Seeds stock through raw ORM on purpose, like the other order API tests.
    stock_ledger_guard = False

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)

        cls.admin_user = cls._user("9000000901", "Sales Admin")
        Admin.objects.create(
            user=cls.admin_user, created_by=cls.superuser, can_update_stock_count=True
        )
        cls.sales_person = cls._user("9000000902", "Sales One")
        SalesPerson.objects.create(
            user=cls.sales_person, city=cls.city, created_by=cls.superuser
        )
        cls.other_sales_person = cls._user("9000000903", "Sales Two")
        SalesPerson.objects.create(
            user=cls.other_sales_person, city=cls.city, created_by=cls.superuser
        )

        cls.acme = cls._client("Acme Seeds", "27AAPFU0939F1ZV", cls.sales_person)
        cls.rival = cls._client("Rival Seeds", "27AAPFU0939F1ZB", cls.other_sales_person)
        verify_client(cls.acme, cls.admin_user)
        verify_client(cls.rival, cls.admin_user)

        product = Product.objects.create(
            name="Alpha Seed",
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )
        cls.bag = ProductPackaging.objects.create(
            product=product,
            packet_weight=W1,
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=cls.superuser,
        )
        cls.product = product
        book_raw_material_for_every_product(actor=cls.superuser)

    @classmethod
    def _user(cls, phone, name):
        return User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )

    @classmethod
    def _client(cls, company_name, gst, actor):
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
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": f"{company_name} Transport"}],
            actor=actor,
        )

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    # -- helpers --------------------------------------------------------------

    def _as_android(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def _as_web(self, user):
        self.client = APIClient()
        self.client.force_login(user)

    def _address(self, **overrides):
        data = {
            "line_1": "9 Mill Road",
            "line_2": "",
            "pincode": "394185",
            "city": self.city.id,
            "state": self.state.id,
            "country": self.country.id,
        }
        data.update(overrides)
        return data

    def _booked_for(self, **overrides):
        data = {
            "party_name": "Shree Krishna Traders",
            "village_name": "Kamrej",
            "address": self._address(),
        }
        data.update(overrides)
        return data

    def _bag_body(self, **overrides):
        body = {
            "client_public_id": self.acme.public_id,
            "client_address_id": self.acme.client_addresses.first().id,
            "items": [{"product_packaging_public_id": self.bag.public_id, "quantity": 2}],
        }
        body.update(overrides)
        return body

    def _android_book(self, **overrides):
        self._as_android(self.sales_person)
        return self.client.post(ANDROID_CREATE, self._bag_body(**overrides), format="json")

    def _bag_order(self, **kwargs):
        return create_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.first().address,
            actor=self.sales_person,
            items=[{"product_packaging": self.bag, "quantity": 2}],
            **kwargs,
        )

    def _child(self, client=None, **kwargs):
        from aggregator.ClientChildOrgOperations import resolve_child_org

        data = {
            "party_name": "Shree Krishna Traders",
            "village_name": "Kamrej",
            "client_address_id": (client or self.acme).client_addresses.first().id,
        }
        data.update(kwargs)
        return resolve_child_org(client or self.acme, data, self.sales_person)

    def _count_loose(self, packets=100):
        inv.record_loose_stocks(
            counts={(self.product, W1): packets}, actor=self.admin_user
        )

    def _custom_body(self, **overrides):
        body = {
            "client_public_id": self.acme.public_id,
            "client_address_id": self.acme.client_addresses.first().id,
            "items": [
                {
                    "product_public_id": self.product.public_id,
                    "packet_weight": "1.000",
                    "packets": 3,
                }
            ],
        }
        body.update(overrides)
        return body

    def _custom_order(self, **kwargs):
        self._count_loose()
        return create_custom_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.first().address,
            actor=self.admin_user,
            items=[{"product": self.product, "packet_weight": W1, "packets": 3}],
            **kwargs,
        )

    # -- Android booking ------------------------------------------------------

    def test_without_booked_for_the_response_carries_a_null_key(self):
        response = self._android_book()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn("booked_for", response.data)
        self.assertIsNone(response.data["booked_for"])
        self.assertIsNone(Order.objects.get().booked_for)
        self.assertFalse(ClientChildOrg.objects.exists())

    def test_a_null_booked_for_is_treated_as_absent(self):
        response = self._android_book(booked_for=None)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data["booked_for"])

    def test_a_new_booked_for_creates_the_child_and_attaches_it(self):
        response = self._android_book(
            booked_for=self._booked_for(
                transport_name="Patel Roadways", contact_number="9876543210"
            )
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        child = ClientChildOrg.objects.get()
        self.assertEqual(Order.objects.get().booked_for, child)
        self.assertEqual(child.client, self.acme)
        booked = response.data["booked_for"]
        self.assertEqual(booked["id"], child.id)
        self.assertEqual(booked["party_name"], "Shree Krishna Traders")
        self.assertEqual(booked["transport_name"], "Patel Roadways")
        self.assertEqual(booked["address"]["pincode"], "394185")

    def test_booking_again_with_the_same_pair_reuses_the_child(self):
        self._android_book(booked_for=self._booked_for())
        response = self._android_book(
            booked_for={"party_name": " shree krishna traders", "village_name": "KAMREJ"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(ClientChildOrg.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 2)

    def test_booking_by_id_reuses_the_child(self):
        child = self._child()
        response = self._android_book(booked_for={"id": child.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["booked_for"]["id"], child.id)

    def test_another_clients_child_id_is_refused(self):
        child = self._child(client=self.rival)
        response = self._android_book(booked_for={"id": child.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No such child org for this client", response.data["detail"])
        self.assertFalse(Order.objects.exists())

    def test_a_mismatch_is_refused_and_no_order_is_created(self):
        self._child(contact_number="9876500000")
        response = self._android_book(
            booked_for={
                "party_name": "Shree Krishna Traders",
                "village_name": "Kamrej",
                "contact_number": "9876511111",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("contact_number", response.data["detail"])
        self.assertFalse(Order.objects.exists())

    def test_a_failing_order_leaves_no_child_behind(self):
        response = self._android_book(
            booked_for=self._booked_for(),
            items=[{"product_packaging_public_id": "PP-NOPE", "quantity": 1}],
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ClientChildOrg.objects.exists())

    def test_a_new_child_without_an_address_is_refused(self):
        response = self._android_book(
            booked_for={"party_name": "Shree Krishna", "village_name": "Kamrej"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("address or client_address_id is required", response.data["detail"])
        self.assertFalse(Order.objects.exists())

    def test_both_address_forms_are_refused(self):
        link = self.acme.client_addresses.first()
        response = self._android_book(
            booked_for=self._booked_for(client_address_id=link.id)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_a_foreign_address_link_is_refused(self):
        foreign = self.rival.client_addresses.first()
        response = self._android_book(
            booked_for={
                "party_name": "Shree Krishna",
                "village_name": "Kamrej",
                "client_address_id": foreign.id,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ClientChildOrg.objects.exists())

    def test_an_empty_booked_for_is_refused(self):
        response = self._android_book(booked_for={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_delivery_address_is_not_the_childs(self):
        response = self._android_book(booked_for=self._booked_for())
        order = Order.objects.get()
        self.assertEqual(
            order.delivery_address, self.acme.client_addresses.first().address
        )
        self.assertNotEqual(order.delivery_address, order.booked_for.address)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_the_android_list_carries_the_short_form(self):
        child = self._child()
        self._bag_order(booked_for=child)
        self._bag_order()
        self._as_android(self.sales_person)
        rows = self.client.get(ANDROID_ORDERS).data["results"]
        booked = {row["booked_for"] is not None for row in rows}
        self.assertEqual(booked, {True, False})
        row = next(row for row in rows if row["booked_for"])
        self.assertEqual(
            row["booked_for"],
            {"id": child.id, "party_name": "Shree Krishna Traders", "village_name": "Kamrej"},
        )

    # -- Admin custom order booking -------------------------------------------

    def test_custom_order_without_booked_for_has_a_null_key(self):
        self._count_loose()
        self._as_web(self.admin_user)
        response = self.client.post(CREATE_CUSTOM, self._custom_body(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data["booked_for"])

    def test_custom_order_creates_and_attaches_a_child(self):
        self._count_loose()
        self._as_web(self.admin_user)
        response = self.client.post(
            CREATE_CUSTOM,
            self._custom_body(booked_for=self._booked_for()),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        child = ClientChildOrg.objects.get()
        self.assertEqual(CustomOrder.objects.get().booked_for, child)
        self.assertEqual(response.data["booked_for"]["id"], child.id)

    def test_custom_order_failure_rolls_back_the_child(self):
        self._count_loose(1)
        self._as_web(self.admin_user)
        response = self.client.post(
            CREATE_CUSTOM,
            self._custom_body(booked_for=self._booked_for()),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ClientChildOrg.objects.exists())
        self.assertFalse(CustomOrder.objects.exists())

    def test_custom_order_mismatch_is_refused(self):
        self._count_loose()
        self._child(transport_name="Patel Roadways")
        self._as_web(self.admin_user)
        response = self.client.post(
            CREATE_CUSTOM,
            self._custom_body(
                booked_for={
                    "party_name": "Shree Krishna Traders",
                    "village_name": "Kamrej",
                    "transport_name": "Other",
                }
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomOrder.objects.exists())

    # -- Admin edit -----------------------------------------------------------

    def _edit_order(self, order, body):
        self._as_web(self.admin_user)
        return self.client.patch(
            EDIT_ORDER.format(public_id=order.public_id), body, format="json"
        )

    def _edit_custom(self, order, body):
        self._as_web(self.admin_user)
        return self.client.patch(
            EDIT_CUSTOM.format(public_id=order.public_id), body, format="json"
        )

    def test_edit_order_omitting_booked_for_leaves_it_alone(self):
        child = self._child()
        order = self._bag_order(booked_for=child)
        response = self._edit_order(order, {"special_comments": "note"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["booked_for"]["id"], child.id)
        order.refresh_from_db()
        self.assertEqual(order.booked_for, child)

    def test_edit_order_null_clears_booked_for(self):
        order = self._bag_order(booked_for=self._child())
        response = self._edit_order(order, {"booked_for": None})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIsNone(response.data["booked_for"])
        order.refresh_from_db()
        self.assertIsNone(order.booked_for)

    def test_edit_order_object_sets_booked_for(self):
        order = self._bag_order()
        response = self._edit_order(order, {"booked_for": self._booked_for()})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.booked_for, ClientChildOrg.objects.get())
        self.assertEqual(response.data["booked_for"]["party_name"], "Shree Krishna Traders")

    def test_edit_order_with_another_clients_child_is_refused(self):
        foreign = self._child(client=self.rival)
        order = self._bag_order()
        response = self._edit_order(order, {"booked_for": {"id": foreign.id}})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertIsNone(order.booked_for)

    def test_edit_order_failure_rolls_back_a_new_child(self):
        order = self._bag_order()
        response = self._edit_order(
            order,
            {
                "booked_for": self._booked_for(),
                "items": [{"product_packaging_public_id": "PP-NOPE", "quantity": 1}],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ClientChildOrg.objects.exists())

    def test_a_dispatched_order_refuses_a_booked_for_edit(self):
        order = self._dispatched_order()
        response = self._edit_order(order, {"booked_for": self._booked_for()})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ClientChildOrg.objects.exists())

    def test_edit_custom_order_omit_clear_and_set(self):
        child = self._child()
        order = self._custom_order(booked_for=child)

        response = self._edit_custom(order, {"special_comments": "note"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["booked_for"]["id"], child.id)

        response = self._edit_custom(order, {"booked_for": None})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIsNone(response.data["booked_for"])

        response = self._edit_custom(order, {"booked_for": {"id": child.id}})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.booked_for, child)

    def test_model_rejects_a_foreign_childs_order(self):
        foreign = self._child(client=self.rival)
        order = self._bag_order()
        order.booked_for = foreign
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as caught:
            order.full_clean()
        self.assertIn("booked_for", caught.exception.message_dict)

    # -- Details, lists and exports -------------------------------------------

    def test_order_and_custom_order_detail_list_and_export_carry_booked_for(self):
        child = self._child()
        order = self._bag_order(booked_for=child)
        custom = self._custom_order(booked_for=child)
        self._as_web(self.admin_user)

        detail = self.client.get(ORDER_DETAIL.format(public_id=order.public_id)).data
        self.assertEqual(detail["booked_for"]["id"], child.id)
        detail = self.client.get(CUSTOM_DETAIL.format(public_id=custom.public_id)).data
        self.assertEqual(detail["booked_for"]["id"], child.id)

        short = {"id": child.id, "party_name": "Shree Krishna Traders", "village_name": "Kamrej"}
        self.assertEqual(self.client.get(ORDERS).data["results"][0]["booked_for"], short)
        self.assertEqual(self.client.get(CUSTOM_ORDERS).data["results"][0]["booked_for"], short)

        window = self._export_window()
        exported = self.client.get(EXPORT_ORDERS, window).data
        self.assertEqual(self._rows(exported)[0]["booked_for"]["id"], child.id)
        exported = self.client.get(EXPORT_CUSTOM, window).data
        self.assertEqual(self._rows(exported)[0]["booked_for"]["id"], child.id)

    def test_list_rows_without_a_child_carry_null(self):
        self._bag_order()
        self._as_web(self.admin_user)
        self.assertIsNone(self.client.get(ORDERS).data["results"][0]["booked_for"])

    def test_listing_orders_does_not_query_per_row(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def queries() -> int:
            with CaptureQueriesContext(connection) as captured:
                self.client.get(ORDERS)
            return len(captured)

        child = self._child()
        self._as_web(self.admin_user)
        orders = [self._bag_order() for _ in range(4)]
        without = queries()
        Order.objects.filter(pk__in=[order.pk for order in orders]).update(booked_for=child)
        # Reading booked_for adds nothing: it is joined, not fetched per row.
        self.assertEqual(queries(), without)

    @staticmethod
    def _export_window():
        today = indian_now().date()
        return {
            "start_date": (today - timedelta(days=1)).isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
        }

    def _window(self):
        now = indian_now()
        return {
            "start_date_time": (now - timedelta(days=1)).isoformat(),
            "end_date_time": (now + timedelta(days=1)).isoformat(),
        }

    @staticmethod
    def _rows(payload):
        return payload["results"] if isinstance(payload, dict) and "results" in payload else payload

    # -- Challans -------------------------------------------------------------

    def _dispatched_order(self, **kwargs):
        order = self._bag_order(**kwargs)
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), 400),
            actor=self.admin_user,
        )
        self._as_web(self.admin_user)
        self.client.post(VERIFY.format(public_id=order.public_id), {}, format="json")
        response = self.client.post(
            DISPATCH.format(public_id=order.public_id),
            {
                "from_city_id": self.city.id,
                "driver_name": "Ramesh Driver",
                "driver_number": "9876500002",
                "vehicle_number": "GJ05AB1234",
                "items": [
                    {
                        "product_packaging_public_id": self.bag.public_id,
                        "lot_number": "LOT-2026-01",
                    }
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        order.refresh_from_db()
        return order

    def test_the_challan_carries_booked_for_next_to_the_receiver(self):
        child = self._child(transport_name="Patel Roadways")
        order = self._dispatched_order(booked_for=child)

        self._as_web(self.admin_user)
        challan = self.client.get(CHALLANS, self._window()).data["results"][0]
        self.assertEqual(challan["order_public_id"], order.public_id)
        self.assertEqual(challan["booked_for"]["id"], child.id)
        self.assertEqual(challan["booked_for"]["transport_name"], "Patel Roadways")
        self.assertEqual(challan["booked_for"]["address"]["city"], "Surat")
        self.assertEqual(challan["receiver_details"]["company_name"], "Acme Seeds")

        receipts = self._rows(self.client.get(RECEIPTS, self._export_window()).data)
        self.assertEqual(receipts[0]["booked_for"]["id"], child.id)

        self._as_android(self.sales_person)
        rows = self.client.get(ANDROID_CHALLANS, self._window()).data["results"]
        self.assertEqual(rows[0]["booked_for"]["id"], child.id)
        one = self.client.get(ANDROID_CHALLAN.format(public_id=order.public_id)).data
        self.assertEqual(one["booked_for"]["id"], child.id)

    def test_a_challan_without_a_child_carries_null(self):
        self._dispatched_order()
        self._as_web(self.admin_user)
        challan = self.client.get(CHALLANS, self._window()).data["results"][0]
        self.assertIn("booked_for", challan)
        self.assertIsNone(challan["booked_for"])

    # -- Pickers --------------------------------------------------------------

    def test_the_android_picker_lists_the_clients_children(self):
        zed = self._child(party_name="Zed Traders")
        alpha = self._child(party_name="Alpha Traders")
        self._child(client=self.rival)
        self._as_android(self.sales_person)
        response = self.client.get(ANDROID_CHILDREN, {"client_public_id": self.acme.public_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual([row["id"] for row in response.data], [alpha.id, zed.id])
        self.assertEqual(
            set(response.data[0]),
            {"id", "party_name", "village_name", "transport_name", "contact_number", "address"},
        )

    def test_the_android_picker_hides_another_sales_persons_client(self):
        self._child(client=self.rival)
        self._as_android(self.sales_person)
        response = self.client.get(
            ANDROID_CHILDREN, {"client_public_id": self.rival.public_id}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_the_android_picker_requires_a_client(self):
        self._as_android(self.sales_person)
        response = self.client.get(ANDROID_CHILDREN)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_web_picker_is_unscoped_for_admins(self):
        mine = self._child()
        theirs = self._child(client=self.rival)
        self._as_web(self.admin_user)
        for client, child in ((self.acme, mine), (self.rival, theirs)):
            response = self.client.get(WEB_CHILDREN, {"client_public_id": client.public_id})
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual([row["id"] for row in response.data], [child.id])

    def test_the_web_picker_refuses_a_non_admin(self):
        self._as_web(self.sales_person)
        response = self.client.get(WEB_CHILDREN, {"client_public_id": self.acme.public_id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_the_web_picker_404s_an_unknown_client(self):
        self._as_web(self.admin_user)
        response = self.client.get(WEB_CHILDREN, {"client_public_id": "C-NOPE"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
