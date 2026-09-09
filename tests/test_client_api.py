"""Sales-admin client endpoints: verify-client, update-client and get-clients.

Session-only web endpoints, exercised over the ``WebApiTestCase`` baseline.
Clients themselves are born on the Android side, so these tests build them
through ``ClientOperations`` directly.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import create_client_with_details
from aggregator.models import City, Country, State
from authentication.models import Admin, SalesPerson
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

VERIFY_CLIENT_URL = "/api/sales-admin/verify-client/"
UPDATE_CLIENT_URL = "/api/sales-admin/update-client/"
GET_CLIENTS_URL = "/api/sales-admin/get-clients/"

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

        cls.sales_person = User.objects.create_user(
            phone_number="9000000001",
            name="Sales One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(
            user=cls.sales_person, city=cls.city, created_by=cls.superuser
        )

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

    # -- the list stub --------------------------------------------------------

    def test_get_clients_is_still_work_in_progress(self):
        """tests/test_client_api.py::SalesAdminClientApiTest::test_get_clients_is_still_work_in_progress"""
        self.login_as(self.admin_user)

        response = self.client.get(GET_CLIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)
