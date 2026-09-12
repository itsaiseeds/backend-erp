"""Sales-admin client endpoints: verify-client, update-client and get-clients.

Session-only web endpoints, exercised over the ``WebApiTestCase`` baseline.
Clients themselves are born on the Android side, so these tests build them
through ``ClientOperations`` directly.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import create_client_with_details, verify_client
from aggregator.models import City, Country, State
from authentication.models import Admin, SalesPerson
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

VERIFY_CLIENT_URL = "/api/sales-admin/verify-client/"
UPDATE_CLIENT_URL = "/api/sales-admin/update-client/"
GET_CLIENTS_URL = "/api/sales-admin/get-clients/"
CLIENT_URL = "/api/sales-admin/client/{public_id}"

GST = "27AAPFU0939F1ZV"


class SalesAdminClientApiTest(WebApiTestCase):
    """Cover verification, admin-only core edits and the list stub.

    tests/test_client_api.py::SalesAdminClientApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Two sales people who own clients, and the admin who verifies them."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        # India / Gujarat / Surat / Ahmedabad are part of the dml.sql baseline.
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.other_city = City.objects.get(name="Ahmedabad", state=cls.state)

        cls.sales_person = cls._make_sales_person("9000000001", "Sales One")
        cls.other_sales_person = cls._make_sales_person("9000000004", "Sales Two")

        cls.admin_user = User.objects.create_user(
            phone_number="9000000002",
            name="Sales Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)

    @classmethod
    def _make_sales_person(cls, phone, name):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(user=user, city=cls.city, created_by=cls.superuser)
        return user

    # 15-char GSTINs differing only in the final char (see validate_gst_number).
    _GST_SUFFIXES = "013456789ACDEFGHIJKLMNOPQRSTUWXY"

    def _make_client(
        self,
        *,
        company_name,
        gst_index,
        actor=None,
        city=None,
        line_1="1 Ring Road",
        pincode="395007",
    ):
        city = city or self.city
        return create_client_with_details(
            company_name=company_name,
            company_phone="9876543210",
            gst_number=f"27AAPFU0939F1Z{self._GST_SUFFIXES[gst_index]}",
            addresses=[
                {
                    "line_1": line_1,
                    "pincode": pincode,
                    "city": city,
                    "state": self.state,
                    "country": self.country,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": "ABC Transport"}],
            actor=actor or self.sales_person,
        )

    def setUp(self):
        super().setUp()
        self.pending = create_client_with_details(
            company_name="Acme Seeds",
            company_phone="9876543210",
            gst_number=GST,
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "pincode": "395007",
                    "city": self.city,
                    "state": self.state,
                    "country": self.country,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": "ABC Transport"}],
            actor=self.sales_person,
        )

    # -- verification ---------------------------------------------------------

    def test_verifying_records_the_admin_and_cannot_be_repeated(self):
        """The first verify stamps who and when; a second one is a 400.

        tests/test_client_api.py::SalesAdminClientApiTest::test_verifying_records_the_admin_and_cannot_be_repeated
        """
        self.login_as(self.admin_user)
        body = {"public_id": self.pending.public_id}

        response = self.client.post(VERIFY_CLIENT_URL, body, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "VERIFIED")
        self.assertTrue(response.data["is_verified"])
        self.assertEqual(response.data["verified_by"], "Sales Admin")
        self.assertIsNotNone(response.data["verified_at"])

        repeat = self.client.post(VERIFY_CLIENT_URL, body, format="json")
        self.assertEqual(repeat.status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_unknown_client_is_not_found(self):
        """Both the verify and the detail endpoint 404 on an unknown public id.

        tests/test_client_api.py::SalesAdminClientApiTest::test_an_unknown_client_is_not_found
        """
        self.login_as(self.admin_user)

        self.assertEqual(
            self.client.post(
                VERIFY_CLIENT_URL, {"public_id": "C-NOPE"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get(CLIENT_URL.format(public_id="C-NOPE")).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # -- admin updates --------------------------------------------------------

    def test_an_admin_update_writes_only_what_it_names(self):
        """Core fields are writable, omitted lists survive untouched, and the
        verification fields are read-only on this endpoint.

        tests/test_client_api.py::SalesAdminClientApiTest::test_an_admin_update_writes_only_what_it_names
        """
        self.login_as(self.admin_user)

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {
                "public_id": self.pending.public_id,
                "company_name": "Acme Seeds Pvt Ltd",
                # Sent but ignored: verification happens through verify-client.
                "status": "VERIFIED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["company_name"], "Acme Seeds Pvt Ltd")
        self.assertEqual(response.data["status"], "VERIFICATION_PENDING")
        # No list was named, so all three are left exactly as they were.
        self.assertEqual(len(response.data["addresses"]), 1)
        self.assertEqual(len(response.data["contacts"]), 1)
        self.assertEqual(len(response.data["transport_agencies"]), 1)

    def test_a_named_list_is_replaced_wholesale_and_may_not_be_emptied(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_a_named_list_is_replaced_wholesale_and_may_not_be_emptied"""
        self.login_as(self.admin_user)

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {
                "public_id": self.pending.public_id,
                "contacts": [{"name": "Suresh", "phone_number": "9876500002"}],
            },
            format="json",
        )
        self.assertEqual(
            [contact["name"] for contact in response.data["contacts"]], ["Suresh"]
        )
        self.assertTrue(response.data["contacts"][0]["is_primary"])

        # Replacing a list with nothing would leave the client with no contact.
        emptied = self.client.post(
            UPDATE_CLIENT_URL,
            {"public_id": self.pending.public_id, "contacts": []},
            format="json",
        )
        self.assertEqual(emptied.status_code, status.HTTP_400_BAD_REQUEST)

    # -- the client list ----------------------------------------------------

    def test_no_filter_returns_every_client_and_the_catalogues(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_no_filter_returns_every_client_and_the_catalogues"""
        self._make_client(company_name="Beta Seeds", gst_index=1, actor=self.other_sales_person)
        self.login_as(self.admin_user)

        response = self.client.get(GET_CLIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 2)
        self.assertEqual(
            sorted(c["company_name"] for c in response.data["results"]),
            ["Acme Seeds", "Beta Seeds"],
        )
        self.assertEqual(
            [
                (f["filter"], f["label"], f["kind"])
                for f in response.data["available_filters"]
            ],
            [
                ("created_by", "Created By", "select"),
                ("verified_by", "Verified By", "select"),
                ("city_id", "City", "select"),
                ("status", "Status", "select"),
                ("company_name", "Company Name", "text"),
                ("address", "Address", "text"),
                ("created", "Created", "datetime_range"),
            ],
        )
        self.assertEqual(
            [(s["sort"], s["label"]) for s in response.data["available_sorts"]],
            [("created_at", "Created"), ("company_name", "Company Name")],
        )

    def test_a_card_names_the_sales_person_and_the_verifying_admin(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_a_card_names_the_sales_person_and_the_verifying_admin"""
        self.login_as(self.admin_user)

        card = self.client.get(GET_CLIENTS_URL).data["results"][0]
        self.assertEqual(card["company_name"], "Acme Seeds")
        self.assertEqual(card["created_by"], "Sales One")
        self.assertEqual(card["primary_contact"]["phone_number"], "9876500001")
        self.assertEqual(card["primary_address"]["pincode"], "395007")
        # Unverified: the field is present but null.
        self.assertIsNone(card["verified_by"])

        self.client.post(
            VERIFY_CLIENT_URL, {"public_id": self.pending.public_id}, format="json"
        )

        card = self.client.get(GET_CLIENTS_URL).data["results"][0]
        self.assertEqual(card["verified_by"], "Sales Admin")

    def test_verified_by_options_skip_clients_nobody_has_verified(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_verified_by_options_skip_clients_nobody_has_verified"""
        self.login_as(self.admin_user)

        def verified_by_options():
            entries = self.client.get(GET_CLIENTS_URL).data["available_filters"]
            entry = next(f for f in entries if f["filter"] == "verified_by")
            return entry["options"]

        # Nothing verified yet -- an all-null column must offer no choices at
        # all, rather than a "None" entry that cannot be sent as a filter value.
        self.assertEqual(verified_by_options(), [])

        self.client.post(
            VERIFY_CLIENT_URL, {"public_id": self.pending.public_id}, format="json"
        )

        self.assertEqual(
            verified_by_options(),
            [{"value": self.admin_user.id, "label": "Sales Admin"}],
        )

    def test_every_declared_filter_narrows_the_list(self):
        """One fixture pair, then each filter in turn -- the generic filter
        machinery itself is unit-tested in ``tests/test_paginated_filters.py``,
        so what is checked here is that each declared filter is wired to the
        column it claims.

        tests/test_client_api.py::SalesAdminClientApiTest::test_every_declared_filter_narrows_the_list
        """
        # Acme Seeds (from setUp): Sales One, Surat, unverified.
        # Beta Traders: Sales Two, Ahmedabad, verified by the admin.
        beta = self._make_client(
            company_name="Beta Traders",
            gst_index=1,
            actor=self.other_sales_person,
            city=self.other_city,
            pincode="380001",
        )
        verify_client(beta, self.admin_user)
        self.login_as(self.admin_user)

        cases = [
            ("created_by", {"created_by": str(self.other_sales_person.id)}, ["Beta Traders"]),
            ("verified_by", {"verified_by": str(self.admin_user.id)}, ["Beta Traders"]),
            ("city_id", {"city_id": str(self.other_city.id)}, ["Beta Traders"]),
            ("status", {"status": "VERIFIED"}, ["Beta Traders"]),
            ("company_name substring", {"company_name": "cme se"}, ["Acme Seeds"]),
        ]
        for label, query, expected in cases:
            with self.subTest(filter=label):
                response = self.client.get(GET_CLIENTS_URL, query)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    [c["company_name"] for c in response.data["results"]], expected
                )

        # The created_by catalogue lists every sales person with a client.
        options = next(
            f for f in self.client.get(GET_CLIENTS_URL).data["available_filters"]
            if f["filter"] == "created_by"
        )["options"]
        self.assertEqual(sorted(o["label"] for o in options), ["Sales One", "Sales Two"])

    def test_sorting_and_pagination(self):
        """Default order is newest first, ``company_name`` is alphabetical, an
        unknown sort is a 400, and pages are 10 long.

        tests/test_client_api.py::SalesAdminClientApiTest::test_sorting_and_pagination
        """
        for index in range(1, 12):
            self._make_client(company_name=f"Client {index:02d}", gst_index=index)
        zeta = self._make_client(company_name="Zeta Seeds", gst_index=12)
        self.login_as(self.admin_user)

        page_1 = self.client.get(GET_CLIENTS_URL)
        self.assertEqual(page_1.data["total_count"], 13)
        self.assertEqual(len(page_1.data["results"]), 10)
        self.assertEqual(page_1.data["next_page_number"], 2)
        # Newest first by default: Zeta was created last.
        self.assertEqual(page_1.data["results"][0]["company_name"], zeta.company_name)

        page_2 = self.client.get(GET_CLIENTS_URL, {"page": 2})
        self.assertEqual(len(page_2.data["results"]), 3)
        self.assertIsNone(page_2.data["next_page_number"])

        by_name = self.client.get(GET_CLIENTS_URL, {"sort": "company_name"})
        self.assertEqual(by_name.data["results"][0]["company_name"], "Acme Seeds")

        self.assertEqual(
            self.client.get(GET_CLIENTS_URL, {"sort": "gst_number"}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # -- single client detail -----------------------------------------------

    def test_an_admin_gets_any_client_in_full(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_an_admin_gets_any_client_in_full"""
        self.login_as(self.admin_user)

        response = self.client.get(CLIENT_URL.format(public_id=self.pending.public_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.data
        self.assertEqual(body["public_id"], self.pending.public_id)
        self.assertEqual(body["company_name"], "Acme Seeds")
        self.assertEqual(body["gst_number"], GST)
        self.assertEqual([a["line_1"] for a in body["addresses"]], ["1 Ring Road"])
        self.assertEqual([c["name"] for c in body["contacts"]], ["Ramesh"])
        self.assertEqual(
            [t["name"] for t in body["transport_agencies"]], ["ABC Transport"]
        )

    def test_client_detail_reflects_verification(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_client_detail_reflects_verification"""
        self.login_as(self.admin_user)
        self.client.post(
            VERIFY_CLIENT_URL, {"public_id": self.pending.public_id}, format="json"
        )

        body = self.client.get(
            CLIENT_URL.format(public_id=self.pending.public_id)
        ).data

        self.assertEqual(body["status"], "VERIFIED")
        self.assertTrue(body["is_verified"])
        self.assertEqual(body["verified_by"], self.admin_user.name)
