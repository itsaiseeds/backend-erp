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
        """A sales person who owns a client, an admin, and a plain user."""
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

        cls.plain = User.objects.create_user(
            phone_number="9000000003",
            name="Plain User",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )

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

    # -- permission gating ----------------------------------------------------

    def test_a_sales_person_cannot_verify_a_client(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_a_sales_person_cannot_verify_a_client"""
        self.login_as(self.sales_person)

        response = self.client.post(
            VERIFY_CLIENT_URL, {"public_id": self.pending.public_id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_requests_are_rejected(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_anonymous_requests_are_rejected"""
        self.assertIn(self.client.get(GET_CLIENTS_URL).status_code, (401, 403))

    # -- verification ---------------------------------------------------------

    def test_verifying_records_the_admin_and_the_time(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_verifying_records_the_admin_and_the_time"""
        self.login_as(self.admin_user)

        response = self.client.post(
            VERIFY_CLIENT_URL, {"public_id": self.pending.public_id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "VERIFIED")
        self.assertTrue(response.data["is_verified"])
        self.assertEqual(response.data["verified_by"], "Sales Admin")
        self.assertIsNotNone(response.data["verified_at"])

    def test_a_client_cannot_be_verified_twice(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_a_client_cannot_be_verified_twice"""
        self.login_as(self.admin_user)
        body = {"public_id": self.pending.public_id}
        self.client.post(VERIFY_CLIENT_URL, body, format="json")

        response = self.client.post(VERIFY_CLIENT_URL, body, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_unknown_client_is_not_found(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_an_unknown_client_is_not_found"""
        self.login_as(self.admin_user)

        response = self.client.post(
            VERIFY_CLIENT_URL, {"public_id": "C-NOPE"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- admin updates --------------------------------------------------------

    def test_an_admin_may_change_the_core_details(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_an_admin_may_change_the_core_details"""
        self.login_as(self.admin_user)

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {"public_id": self.pending.public_id, "company_name": "Acme Seeds Pvt Ltd"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["company_name"], "Acme Seeds Pvt Ltd")

    def test_a_list_left_out_is_untouched(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_a_list_left_out_is_untouched"""
        self.login_as(self.admin_user)

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {"public_id": self.pending.public_id, "company_phone": "9876500009"},
            format="json",
        )

        self.assertEqual(len(response.data["addresses"]), 1)
        self.assertEqual(len(response.data["contacts"]), 1)
        self.assertEqual(len(response.data["transport_agencies"]), 1)

    def test_an_admin_may_replace_a_list(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_an_admin_may_replace_a_list"""
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

    def test_an_emptied_list_is_rejected(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_an_emptied_list_is_rejected"""
        self.login_as(self.admin_user)

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {"public_id": self.pending.public_id, "contacts": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_verification_fields_are_not_writable_here(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_the_verification_fields_are_not_writable_here"""
        self.login_as(self.admin_user)

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {"public_id": self.pending.public_id, "status": "VERIFIED"},
            format="json",
        )

        self.assertEqual(response.data["status"], "VERIFICATION_PENDING")

    # -- the client list ----------------------------------------------------

    def test_get_clients_needs_an_admin(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_get_clients_needs_an_admin"""
        self.login_as(self.sales_person)

        self.assertEqual(self.client.get(GET_CLIENTS_URL).status_code, 403)

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
            [(f["filter"], f["kind"]) for f in response.data["available_filters"]],
            [
                ("created_by", "select"),
                ("city_id", "select"),
                ("status", "select"),
                ("company_name", "text"),
                ("address", "text"),
                ("created", "datetime_range"),
            ],
        )
        self.assertEqual(
            [s["sort"] for s in response.data["available_sorts"]],
            ["created_at", "company_name"],
        )

    def test_the_card_names_the_sales_person_who_created_the_client(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_the_card_names_the_sales_person_who_created_the_client"""
        self.login_as(self.admin_user)

        card = self.client.get(GET_CLIENTS_URL).data["results"][0]

        self.assertEqual(card["company_name"], "Acme Seeds")
        self.assertEqual(card["created_by"], "Sales One")
        self.assertEqual(card["primary_contact"]["phone_number"], "9876500001")
        self.assertEqual(card["primary_address"]["pincode"], "395007")

    def test_filtering_by_created_by(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_filtering_by_created_by"""
        self._make_client(company_name="Beta Seeds", gst_index=1, actor=self.other_sales_person)
        self.login_as(self.admin_user)

        response = self.client.get(
            GET_CLIENTS_URL, {"created_by": str(self.other_sales_person.id)}
        )

        self.assertEqual(
            [c["company_name"] for c in response.data["results"]], ["Beta Seeds"]
        )
        options = response.data["available_filters"][0]["options"]
        self.assertEqual(
            sorted(o["label"] for o in options), ["Sales One", "Sales Two"]
        )

    def test_filtering_by_primary_address_city(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_filtering_by_primary_address_city"""
        self._make_client(
            company_name="Beta Seeds", gst_index=1, city=self.other_city, pincode="380001"
        )
        self.login_as(self.admin_user)

        response = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.other_city.id)})

        self.assertEqual(
            [c["company_name"] for c in response.data["results"]], ["Beta Seeds"]
        )

    def test_filtering_by_status(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_filtering_by_status"""
        beta = self._make_client(company_name="Beta Seeds", gst_index=1)
        verify_client(beta, self.admin_user)
        self.login_as(self.admin_user)

        response = self.client.get(GET_CLIENTS_URL, {"status": "VERIFIED"})

        self.assertEqual(
            [c["company_name"] for c in response.data["results"]], ["Beta Seeds"]
        )

    def test_filtering_by_company_name_substring(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_filtering_by_company_name_substring"""
        self._make_client(company_name="Beta Traders", gst_index=1)
        self.login_as(self.admin_user)

        response = self.client.get(GET_CLIENTS_URL, {"company_name": "cme se"})

        self.assertEqual(
            [c["company_name"] for c in response.data["results"]], ["Acme Seeds"]
        )

    def test_default_sort_is_newest_first_and_company_name_sort_is_alphabetical(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_default_sort_is_newest_first_and_company_name_sort_is_alphabetical"""
        self._make_client(company_name="Zeta Seeds", gst_index=1)
        self.login_as(self.admin_user)

        default = self.client.get(GET_CLIENTS_URL)
        by_name = self.client.get(GET_CLIENTS_URL, {"sort": "company_name"})

        self.assertEqual(
            [c["company_name"] for c in default.data["results"]],
            ["Zeta Seeds", "Acme Seeds"],
        )
        self.assertEqual(
            [c["company_name"] for c in by_name.data["results"]],
            ["Acme Seeds", "Zeta Seeds"],
        )

    def test_an_unknown_sort_is_rejected(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_an_unknown_sort_is_rejected"""
        self.login_as(self.admin_user)

        response = self.client.get(GET_CLIENTS_URL, {"sort": "gst_number"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_results_are_paginated(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_results_are_paginated"""
        for index in range(1, 12):
            self._make_client(company_name=f"Client {index:02d}", gst_index=index)
        self.login_as(self.admin_user)

        page_1 = self.client.get(GET_CLIENTS_URL)
        self.assertEqual(page_1.data["total_count"], 12)
        self.assertEqual(len(page_1.data["results"]), 10)
        self.assertEqual(page_1.data["next_page_number"], 2)

        page_2 = self.client.get(GET_CLIENTS_URL, {"page": 2})
        self.assertEqual(len(page_2.data["results"]), 2)
        self.assertIsNone(page_2.data["next_page_number"])

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

    def test_client_detail_unknown_public_id_is_404(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_client_detail_unknown_public_id_is_404"""
        self.login_as(self.admin_user)

        response = self.client.get(CLIENT_URL.format(public_id="C-NOPE"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_client_detail_needs_an_admin(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_client_detail_needs_an_admin"""
        self.login_as(self.sales_person)

        response = self.client.get(CLIENT_URL.format(public_id=self.pending.public_id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_detail_rejects_anonymous(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_client_detail_rejects_anonymous"""
        response = self.client.get(CLIENT_URL.format(public_id=self.pending.public_id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
