"""Android order booking and its two pickers.

Covers ``POST /android/api/v1/create-multi-select-bag-order`` together with
``GET /android/api/v1/utilities/client-addresses`` and
``.../utilities/client-transport-agencies`` -- the ids the pickers hand out are
the ids the order endpoint takes, and that contract is asserted here because
the frontend depends on it.

Authentication and role gating are proven once in
``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import create_client_with_details, verify_client
from aggregator.models import (
    City,
    Client,
    Country,
    Order,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.models.Status import Status, StatusIds
from authentication.models import Admin, SalesPerson
from tests.android.common import AndroidApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
CREATE_ORDER_URL = "/android/api/v1/create-multi-select-bag-order"
ADDRESSES_URL = "/android/api/v1/utilities/client-addresses"
AGENCIES_URL = "/android/api/v1/utilities/client-transport-agencies"


class AndroidBagOrderApiTest(AndroidApiTestCase):
    """Cover booking an order and the pickers that feed it.

    tests/android/test_bag_orders.py::AndroidBagOrderApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Two sales people, one client each, and two bags to book."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)

        cls.sales_person = cls._sales_person("9000000201", "Sales One")
        cls.other_sales_person = cls._sales_person("9000000202", "Sales Two")

        cls.admin_user = User.objects.create_user(
            phone_number="9000000203",
            name="Sales Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)

        cls.client_row = cls._client(
            cls.sales_person, "Acme Seeds", "27AAPFU0939F1ZV", "ABC Transport"
        )
        cls.other_client = cls._client(
            cls.other_sales_person, "Rival Seeds", "27AAPFU0939F1ZB", "XYZ Transport"
        )
        # Born VERIFICATION_PENDING; only a sales admin can promote them.
        verify_client(cls.client_row, cls.admin_user)
        verify_client(cls.other_client, cls.admin_user)

        cls.pending_client = cls._client(
            cls.sales_person, "Pending Seeds", "27AAPFU0939F1ZG", "PQR Transport"
        )
        cls.pending_address_link = cls.pending_client.client_addresses.first()

        cls.address_link = cls.client_row.client_addresses.first()
        cls.other_address_link = cls.other_client.client_addresses.first()
        cls.agency_link = cls.client_row.client_transport_agencies.first()
        cls.other_agency_link = cls.other_client.client_transport_agencies.first()

        product = Product.objects.create(
            name="Bookable Seed",
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFICATE),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )
        cls.bag = ProductPackaging.objects.create(
            product=product,
            packet_weight=Decimal("1.000"),
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=cls.superuser,
        )
        cls.other_bag = ProductPackaging.objects.create(
            product=product,
            packet_weight=Decimal("2.000"),
            packets=5,
            selling_price=Decimal("1100.00"),
            created_by=cls.superuser,
        )

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
    def _client(cls, actor, company_name, gst, agency_name):
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
            transport_agencies=[{"name": agency_name}],
            actor=actor,
        )

    # -- helpers --------------------------------------------------------------

    def _body(self, **overrides):
        body = {
            "client_public_id": self.client_row.public_id,
            "client_address_id": self.address_link.id,
            "items": [
                {"product_packaging_public_id": self.bag.public_id, "quantity": 3}
            ],
        }
        body.update(overrides)
        return body

    def _post(self, actor=None, **overrides):
        self.login_as(actor or self.sales_person)
        return self.client.post(CREATE_ORDER_URL, self._body(**overrides), format="json")

    def _assert_rejected(self, response, *, fragment):
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertIn(fragment, response.data["detail"])
        self.assertFalse(Order.objects.exists())

    # -- booking --------------------------------------------------------------

    def test_an_order_is_booked_with_the_bag_price(self):
        response = self._post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data
        self.assertTrue(data["public_id"].startswith("ORD-"))
        self.assertEqual(data["status"], "BOOKED")
        self.assertEqual(data["client"]["company_name"], "Acme Seeds")
        # 3 bags at the bag's own list price; 3 x 10 packets.
        self.assertEqual(data["total_amount"], "3000.00")
        self.assertEqual(data["total_packets"], 30)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["negotiated_selling_price"], "1000.00")
        self.assertEqual(data["items"][0]["line_total"], "3000.00")

    def test_the_order_is_owned_by_the_calling_sales_person(self):
        self._post()
        order = Order.objects.get()
        self.assertEqual(order.created_by, self.sales_person)
        self.assertEqual(order.client, self.client_row)

    def test_several_bags_are_booked_as_several_lines(self):
        response = self._post(
            items=[
                {"product_packaging_public_id": self.bag.public_id, "quantity": 1},
                {"product_packaging_public_id": self.other_bag.public_id, "quantity": 2},
            ]
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(response.data["total_amount"], "3200.00")

    def test_a_price_sent_by_the_caller_is_ignored(self):
        """A sales person does not negotiate from the app."""
        response = self._post(
            items=[
                {
                    "product_packaging_public_id": self.bag.public_id,
                    "quantity": 1,
                    "negotiated_selling_price": "1.00",
                }
            ]
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["items"][0]["negotiated_selling_price"], "1000.00")

    def test_special_comments_and_delivery_date_are_stored(self):
        response = self._post(
            special_comments="Deliver before noon",
            expected_delivery_date="2026-12-25",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["special_comments"], "Deliver before noon")
        self.assertEqual(response.data["expected_delivery_date"], "2026-12-25")

    # -- transport agency -----------------------------------------------------

    def test_no_agency_means_a_private_dispatch(self):
        response = self._post()
        self.assertIsNone(response.data["transport_agency"])
        self.assertEqual(response.data["dispatch_mode"], "PRIVATE")
        self.assertIsNone(Order.objects.get().transport_agency)

    def test_an_explicit_null_agency_is_also_a_private_dispatch(self):
        response = self._post(client_transport_agency_id=None)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["dispatch_mode"], "PRIVATE")

    def test_the_clients_own_agency_is_recorded(self):
        response = self._post(client_transport_agency_id=self.agency_link.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            response.data["transport_agency"],
            {
                "id": self.agency_link.transport_agency_id,
                "name": "ABC Transport",
            },
        )
        self.assertEqual(response.data["dispatch_mode"], "AGENCY")
        self.assertEqual(
            Order.objects.get().transport_agency,
            self.agency_link.transport_agency,
        )

    def test_another_clients_agency_is_rejected(self):
        self._assert_rejected(
            self._post(client_transport_agency_id=self.other_agency_link.id),
            fragment="one of this client's agencies",
        )

    # -- client verification ---------------------------------------------------

    def test_an_unverified_client_cannot_be_booked_against(self):
        """A client stays unbookable until a sales admin approves it."""
        self._assert_rejected(
            self._post(
                client_public_id=self.pending_client.public_id,
                client_address_id=self.pending_address_link.id,
            ),
            fragment="is not verified",
        )

    def test_a_client_becomes_bookable_once_verified(self):
        """The same request that was refused succeeds after verification."""
        body = {
            "client_public_id": self.pending_client.public_id,
            "client_address_id": self.pending_address_link.id,
        }
        self._assert_rejected(self._post(**body), fragment="is not verified")

        verify_client(self.pending_client, self.admin_user)

        response = self._post(**body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_a_client_whose_status_is_reverted_stops_being_bookable(self):
        """Un-verifying a client closes the door again."""
        Client.objects.filter(pk=self.client_row.pk).update(
            status=Status.by_id(StatusIds.VERIFICATION_PENDING),
            verified_by=None,
            verified_at=None,
        )
        self._assert_rejected(self._post(), fragment="is not verified")

    def test_a_verified_status_without_a_verifier_is_refused(self):
        """``verified_by`` is checked in its own right, not just the status.

        ``Client.clean()`` keeps status / verified_by / verified_at in step, so
        this state is only reachable by writing round it -- which is exactly why
        the endpoint checks all three rather than trusting the status alone.
        """
        Client.objects.filter(pk=self.client_row.pk).update(verified_by=None)
        self._assert_rejected(self._post(), fragment="is not verified")

    def test_a_verified_status_without_a_verified_at_is_refused(self):
        """``verified_at`` is likewise checked in its own right."""
        Client.objects.filter(pk=self.client_row.pk).update(verified_at=None)
        self._assert_rejected(self._post(), fragment="is not verified")

    def test_an_unverified_client_is_refused_before_anything_else_is_read(self):
        """The verification gate does not depend on the rest of the body."""
        self._assert_rejected(
            self._post(
                client_public_id=self.pending_client.public_id,
                client_address_id=self.pending_address_link.id,
                items=[
                    {"product_packaging_public_id": "PP-NOPE", "quantity": 1}
                ],
            ),
            fragment="is not verified",
        )

    # -- validation -----------------------------------------------------------

    def test_another_sales_persons_client_is_rejected(self):
        self._assert_rejected(
            self._post(client_public_id=self.other_client.public_id),
            fragment="Unknown client",
        )

    def test_an_unknown_client_is_rejected(self):
        self._assert_rejected(
            self._post(client_public_id="C-DOESNOTEXIST"), fragment="Unknown client"
        )

    def test_an_address_belonging_to_another_client_is_rejected(self):
        self._assert_rejected(
            self._post(client_address_id=self.other_address_link.id),
            fragment="one of this client's addresses",
        )

    def test_an_unknown_address_is_rejected(self):
        self._assert_rejected(
            self._post(client_address_id=999999),
            fragment="one of this client's addresses",
        )

    def test_an_empty_item_list_is_rejected(self):
        self._assert_rejected(self._post(items=[]), fragment="At least one item")

    def test_the_same_bag_listed_twice_is_rejected(self):
        self._assert_rejected(
            self._post(
                items=[
                    {"product_packaging_public_id": self.bag.public_id, "quantity": 1},
                    {"product_packaging_public_id": self.bag.public_id, "quantity": 2},
                ]
            ),
            fragment="listed twice",
        )

    def test_a_zero_quantity_is_rejected(self):
        self._assert_rejected(
            self._post(
                items=[
                    {"product_packaging_public_id": self.bag.public_id, "quantity": 0}
                ]
            ),
            fragment="at least 1",
        )

    def test_an_unknown_bag_is_rejected(self):
        self._assert_rejected(
            self._post(
                items=[{"product_packaging_public_id": "PP-NOPE", "quantity": 1}]
            ),
            fragment="Unknown product packaging",
        )

    def test_one_bad_line_rolls_back_the_whole_order(self):
        response = self._post(
            items=[
                {"product_packaging_public_id": self.bag.public_id, "quantity": 1},
                {"product_packaging_public_id": "PP-NOPE", "quantity": 1},
            ]
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    # -- pickers --------------------------------------------------------------

    def test_the_address_picker_lists_the_clients_address_links(self):
        self.login_as(self.sales_person)
        response = self.client.get(
            f"{ADDRESSES_URL}?client_public_id={self.client_row.public_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 1)
        row = response.data[0]
        self.assertEqual(row["id"], self.address_link.id)
        self.assertEqual(row["label"], "Warehouse")
        self.assertTrue(row["is_primary"])
        self.assertEqual(row["city"], "Surat")

    def test_the_agency_picker_lists_the_clients_agency_links(self):
        self.login_as(self.sales_person)
        response = self.client.get(
            f"{AGENCIES_URL}?client_public_id={self.client_row.public_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            list(response.data),
            [{"id": self.agency_link.id, "name": "ABC Transport", "is_primary": True}],
        )

    def test_the_pickers_refuse_another_sales_persons_client(self):
        self.login_as(self.sales_person)
        for url in (ADDRESSES_URL, AGENCIES_URL):
            with self.subTest(url=url):
                response = self.client.get(
                    f"{url}?client_public_id={self.other_client.public_id}"
                )
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_the_pickers_require_a_client_public_id(self):
        self.login_as(self.sales_person)
        for url in (ADDRESSES_URL, AGENCIES_URL):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_picker_ids_are_accepted_verbatim_by_create_order(self):
        """The whole point of the two utilities -- assert the contract holds."""
        self.login_as(self.sales_person)
        query = f"?client_public_id={self.client_row.public_id}"
        address_id = self.client.get(f"{ADDRESSES_URL}{query}").data[0]["id"]
        agency_id = self.client.get(f"{AGENCIES_URL}{query}").data[0]["id"]

        response = self._post(
            client_address_id=address_id, client_transport_agency_id=agency_id
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
