"""An admin with app access books orders for a sales person.

Covers ``created_by`` on ``create-multi-select-bag-order``, the admin-only
``sales_person_id`` look-up param, ``utilities/sales-persons`` and the
``is_sales_admin`` flag on login / reauthenticate. Authentication and role
gating are proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import create_client_with_details, verify_client
from aggregator.models import (
    City,
    Country,
    Order,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from authentication.models import Admin, GodownManager, SalesPerson
from tests.android.common import AndroidApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
CREATE_ORDER_URL = "/android/api/v1/create-multi-select-bag-order"
ADDRESSES_URL = "/android/api/v1/utilities/client-addresses"
AGENCIES_URL = "/android/api/v1/utilities/client-transport-agencies"
CLIENTS_URL = "/android/api/v1/get-clients"
SALES_PERSONS_URL = "/android/api/v1/utilities/sales-persons"
LOGIN_URL = "/android/api/v1/auth/login"
REAUTH_URL = "/android/api/v1/auth/reauthenticate"


class AdminBookingApiTest(AndroidApiTestCase):
    """tests/android/test_admin_booking.py::AdminBookingApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)

        cls.sales_person = cls._user("9000000301", "Sales One")
        SalesPerson.objects.create(user=cls.sales_person, city=cls.city, created_by=cls.superuser)
        # An admin who also has app access: both profiles.
        cls.admin = cls._user("9000000302", "Admin Seller", totp=True)
        Admin.objects.create(user=cls.admin, created_by=cls.superuser)
        SalesPerson.objects.create(user=cls.admin, city=cls.city, created_by=cls.superuser)
        cls.godown_user = cls._user("9000000303", "Godown One")
        GodownManager.objects.create(user=cls.godown_user, created_by=cls.superuser)
        # An admin with no SalesPerson profile -- not in the app at all.
        cls.web_admin = cls._user("9000000304", "Web Admin")
        Admin.objects.create(user=cls.web_admin, created_by=cls.superuser)

        cls.sp_client = cls._client(cls.sales_person, "Acme Seeds", "27AAPFU0939F1ZV")
        cls.admin_client = cls._client(cls.admin, "Admin Seeds", "27AAPFU0939F1ZB")
        verify_client(cls.sp_client, cls.web_admin)
        verify_client(cls.admin_client, cls.web_admin)
        cls.sp_address = cls.sp_client.client_addresses.first()
        cls.admin_address = cls.admin_client.client_addresses.first()

        product = Product.objects.create(
            name="Bookable Seed",
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
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

    @classmethod
    def _user(cls, phone, name, totp=False):
        extra = {"totp_secret": "KRSXG5DSNFXGOIDB", "totp_enabled": True} if totp else {}
        return User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
            **extra,
        )

    @classmethod
    def _client(cls, actor, company_name, gst):
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
            transport_agencies=[{"name": "ABC Transport"}],
            actor=actor,
        )

    def _book(self, actor, client, address, **extra):
        self.login_as(actor)
        body = {
            "client_public_id": client.public_id,
            "client_address_id": address.id,
            "items": [{"product_packaging_public_id": self.bag.public_id, "quantity": 2}],
            **extra,
        }
        return self.client.post(CREATE_ORDER_URL, body, format="json")

    # -- booking --------------------------------------------------------------

    def test_an_admin_books_for_a_sales_person(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_an_admin_books_for_a_sales_person"""
        response = self._book(
            self.admin, self.sp_client, self.sp_address, created_by=self.sales_person.id
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = Order.objects.get()
        self.assertEqual(order.created_by, self.sales_person)
        self.assertEqual(order.client, self.sp_client)

    def test_an_admin_cannot_book_the_admins_own_client_for_a_sales_person(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_an_admin_cannot_book_the_admins_own_client_for_a_sales_person"""
        response = self._book(
            self.admin,
            self.admin_client,
            self.admin_address,
            created_by=self.sales_person.id,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_a_non_admin_cannot_send_created_by(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_a_non_admin_cannot_send_created_by"""
        response = self._book(
            self.sales_person,
            self.sp_client,
            self.sp_address,
            created_by=self.sales_person.id,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Order.objects.exists())

    def test_created_by_must_be_a_sales_person(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_created_by_must_be_a_sales_person"""
        for user_id in (self.godown_user.id, self.web_admin.id, 999999):
            with self.subTest(user_id=user_id):
                response = self._book(
                    self.admin, self.sp_client, self.sp_address, created_by=user_id
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_omitting_created_by_books_as_the_caller(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_omitting_created_by_books_as_the_caller"""
        response = self._book(self.admin, self.admin_client, self.admin_address)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Order.objects.get().created_by, self.admin)

    # -- client look-ups ------------------------------------------------------

    def test_an_admin_reads_a_sales_persons_clients(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_an_admin_reads_a_sales_persons_clients"""
        self.login_as(self.admin)
        params = {"sales_person_id": self.sales_person.id}

        clients = self.client.get(CLIENTS_URL, params)
        self.assertEqual(clients.status_code, status.HTTP_200_OK, clients.data)
        self.assertEqual(
            [row["public_id"] for row in clients.data["results"]],
            [self.sp_client.public_id],
        )
        cities = next(f for f in clients.data["available_filters"] if f["filter"] == "city_id")
        self.assertEqual([o["value"] for o in cities["options"]], [self.city.id])

        addresses = self.client.get(
            ADDRESSES_URL, {"client_public_id": self.sp_client.public_id, **params}
        )
        self.assertEqual(addresses.status_code, status.HTTP_200_OK, addresses.data)
        self.assertEqual([row["id"] for row in addresses.data], [self.sp_address.id])

        agencies = self.client.get(
            AGENCIES_URL, {"client_public_id": self.sp_client.public_id, **params}
        )
        self.assertEqual(agencies.status_code, status.HTTP_200_OK, agencies.data)
        self.assertEqual(len(agencies.data), 1)

    def test_without_the_param_the_lookups_stay_scoped_to_the_caller(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_without_the_param_the_lookups_stay_scoped_to_the_caller"""
        self.login_as(self.admin)

        clients = self.client.get(CLIENTS_URL)
        self.assertEqual(
            [row["public_id"] for row in clients.data["results"]],
            [self.admin_client.public_id],
        )
        other = self.client.get(ADDRESSES_URL, {"client_public_id": self.sp_client.public_id})
        self.assertEqual(other.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_non_admin_cannot_use_sales_person_id(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_a_non_admin_cannot_use_sales_person_id"""
        self.login_as(self.sales_person)
        params = {"sales_person_id": self.sales_person.id}

        self.assertEqual(
            self.client.get(CLIENTS_URL, params).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        for url in (ADDRESSES_URL, AGENCIES_URL):
            response = self.client.get(
                url, {"client_public_id": self.sp_client.public_id, **params}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, url)

    # -- utilities/sales-persons ----------------------------------------------

    def test_an_admin_lists_the_bookable_sales_persons(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_an_admin_lists_the_bookable_sales_persons"""
        self.login_as(self.admin)

        response = self.client.get(SALES_PERSONS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        # Ids and names only, in name order, caller included (the baseline data
        # seeds a sales person of its own, so compare just ours).
        rows = [dict(row) for row in response.data]
        self.assertTrue(all(set(row) == {"id", "name"} for row in rows))
        self.assertEqual(rows, sorted(rows, key=lambda row: (row["name"], row["id"])))
        ours = [row for row in rows if row["id"] in (self.admin.id, self.sales_person.id)]
        self.assertEqual(
            ours,
            [
                {"id": self.admin.id, "name": "Admin Seller"},
                {"id": self.sales_person.id, "name": "Sales One"},
            ],
        )
        listed = {row["id"] for row in rows}
        self.assertNotIn(self.godown_user.id, listed)
        self.assertNotIn(self.web_admin.id, listed)

    def test_a_sales_person_or_godown_manager_cannot_list_them(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_a_sales_person_or_godown_manager_cannot_list_them"""
        for user in (self.sales_person, self.godown_user):
            with self.subTest(user=user.name):
                self.login_as(user)
                self.assertEqual(
                    self.client.get(SALES_PERSONS_URL).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    # -- is_sales_admin -------------------------------------------------------

    def test_reauthenticate_reports_is_sales_admin(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_reauthenticate_reports_is_sales_admin"""
        for user, expected in (
            (self.admin, True),
            (self.sales_person, False),
            (self.godown_user, False),
        ):
            with self.subTest(user=user.name):
                self.login_as(user)
                response = self.client.get(REAUTH_URL)
                self.assertIs(response.data["user"]["is_sales_admin"], expected)

    def test_login_reports_is_sales_admin(self):
        """tests/android/test_admin_booking.py::AdminBookingApiTest::test_login_reports_is_sales_admin"""
        response = self.client.post(
            LOGIN_URL,
            {"phone_number": self.admin.phone_number, "otp": self.admin.totp.now()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertIs(response.data["user"]["is_sales_admin"], True)
