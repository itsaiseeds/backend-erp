"""Android client endpoints: get-clients, create-client and update-client.

Token-only sales-person endpoints, exercised over the ``AndroidApiTestCase``
baseline (DML-seeded, bearer-token auth).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Client, ClientAddress, Country, State, TransportAgency
from authentication.models import Admin, SalesPerson
from tests.android.common import AndroidApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

GET_CLIENTS_URL = "/android/api/v1/get-clients"
CREATE_CLIENT_URL = "/android/api/v1/create-client"
UPDATE_CLIENT_URL = "/android/api/v1/update-client"

GST = "27AAPFU0939F1ZV"
OTHER_GST = "27AAPFU0939F1ZB"


class AndroidClientApiTest(AndroidApiTestCase):
    """Cover client creation, the primary rules and list maintenance.

    tests/android/test_clients.py::AndroidClientApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Two sales people, an admin, and the geography an address needs."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        # India / Gujarat / Surat / Ahmedabad are part of the dml.sql baseline.
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.other_city = City.objects.get(name="Ahmedabad", state=cls.state)

        cls.sales_person = cls._make_sales_person("9000000001", "Sales One", cls.city)
        cls.other_sales_person = cls._make_sales_person(
            "9000000002", "Sales Two", cls.city
        )

        cls.admin_user = User.objects.create_user(
            phone_number="9000000003",
            name="Sales Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)

    @classmethod
    def _make_sales_person(cls, phone, name, city):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(user=user, city=city, created_by=cls.superuser)
        return user

    # -- helpers --------------------------------------------------------------

    def _address(self, line_1="1 Ring Road", pincode="395007", city=None, **extra):
        city = city or self.city
        return {
            "line_1": line_1,
            "pincode": pincode,
            "city": city.id,
            "state": self.state.id,
            "country": self.country.id,
            **extra,
        }

    def _body(self, gst=GST, **overrides):
        body = {
            "company_name": "Acme Seeds",
            "company_phone": "9876543210",
            "gst_number": gst,
            "addresses": [self._address()],
            "contacts": [{"name": "Ramesh", "phone_number": "9876500001"}],
            "transport_agencies": [{"name": "ABC Transport"}],
        }
        body.update(overrides)
        return body

    def _create(self, actor=None, **overrides):
        self.login_as(actor or self.sales_person)
        return self.client.post(
            CREATE_CLIENT_URL, self._body(**overrides), format="json"
        )

    # -- creation -------------------------------------------------------------

    def test_create_client_is_pending_verification(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_create_client_is_pending_verification"""
        response = self._create()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "VERIFICATION_PENDING")
        self.assertFalse(response.data["is_verified"])
        self.assertIsNone(response.data["verified_at"])
        self.assertIsNone(response.data["verified_by"])
        self.assertTrue(response.data["public_id"].startswith("C-"))

    def test_a_lone_entry_is_marked_primary(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_a_lone_entry_is_marked_primary"""
        response = self._create()

        for key in ("addresses", "contacts", "transport_agencies"):
            self.assertTrue(response.data[key][0]["is_primary"], key)

    def test_each_list_needs_at_least_one_entry(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_each_list_needs_at_least_one_entry"""
        for key in ("addresses", "contacts", "transport_agencies"):
            with self.subTest(list=key):
                response = self._create(**{key: []})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_flagged_primary_wins_over_position(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_flagged_primary_wins_over_position"""
        response = self._create(
            contacts=[
                {"name": "Ramesh", "phone_number": "9876500001"},
                {"name": "Suresh", "phone_number": "9876500002", "is_primary": True},
            ]
        )

        primary = [c for c in response.data["contacts"] if c["is_primary"]]
        self.assertEqual([c["name"] for c in primary], ["Suresh"])

    def test_the_same_gst_number_cannot_be_reused(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_the_same_gst_number_cannot_be_reused"""
        self._create()
        response = self._create()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_new_pincode_is_created_on_demand(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_a_new_pincode_is_created_on_demand"""
        response = self._create(addresses=[self._address(pincode="395009")])

        self.assertEqual(response.data["addresses"][0]["pincode"], "395009")

    def test_an_unknown_city_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_unknown_city_is_rejected"""
        body = self._body()
        body["addresses"][0]["city"] = 999999
        self.login_as(self.sales_person)

        response = self.client.post(CREATE_CLIENT_URL, body, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- transport agency naming ---------------------------------------------

    def test_two_clients_may_share_an_agency_name_as_separate_rows(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_two_clients_may_share_an_agency_name_as_separate_rows"""
        self._create()
        response = self._create(actor=self.other_sales_person, gst=OTHER_GST)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TransportAgency.objects.filter(name="ABC Transport").count(), 2)

    def test_one_client_may_not_list_an_agency_name_twice(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_one_client_may_not_list_an_agency_name_twice"""
        response = self._create(
            transport_agencies=[{"name": "ABC Transport"}, {"name": "abc transport"}]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- updates --------------------------------------------------------------

    def test_removing_an_address_leaves_the_survivor_primary(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_removing_an_address_leaves_the_survivor_primary"""
        created = self._create(
            addresses=[self._address(), self._address(line_1="2 Ring Road")]
        )
        body = self._body()
        body["public_id"] = created.data["public_id"]
        body["addresses"] = [self._address(line_1="2 Ring Road")]
        del body["company_name"], body["company_phone"], body["gst_number"]

        response = self.client.post(UPDATE_CLIENT_URL, body, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["addresses"]), 1)
        self.assertEqual(response.data["addresses"][0]["line_1"], "2 Ring Road")
        self.assertTrue(response.data["addresses"][0]["is_primary"])

    def test_an_address_label_round_trips_and_can_be_renamed(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_address_label_round_trips_and_can_be_renamed"""
        created = self._create(addresses=[self._address(label="Warehouse")])
        self.assertEqual(created.data["addresses"][0]["label"], "Warehouse")

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {
                "public_id": created.data["public_id"],
                "addresses": [self._address(label="Billing")],
                "contacts": [{"name": "Ramesh", "phone_number": "9876500001"}],
                "transport_agencies": [{"name": "ABC Transport"}],
            },
            format="json",
        )

        # The label is not part of the match key, so the link is renamed in
        # place rather than unlinked and recreated.
        self.assertEqual(response.data["addresses"][0]["label"], "Billing")
        self.assertEqual(ClientAddress.objects.count(), 1)

    def test_removing_the_last_address_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_removing_the_last_address_is_rejected"""
        created = self._create()

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {
                "public_id": created.data["public_id"],
                "addresses": [],
                "contacts": [{"name": "Ramesh", "phone_number": "9876500001"}],
                "transport_agencies": [{"name": "ABC Transport"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ClientAddress.objects.count(), 1)

    def test_a_sales_person_may_not_update_core_details(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_a_sales_person_may_not_update_core_details"""
        created = self._create()
        body = self._body()
        body["public_id"] = created.data["public_id"]

        response = self.client.post(UPDATE_CLIENT_URL, body, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sales admin", response.data["detail"])

    def test_another_sales_persons_client_is_not_found(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_another_sales_persons_client_is_not_found"""
        created = self._create()
        self.login_as(self.other_sales_person)

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {
                "public_id": created.data["public_id"],
                "addresses": [self._address()],
                "contacts": [{"name": "Ramesh", "phone_number": "9876500001"}],
                "transport_agencies": [{"name": "ABC Transport"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- listing --------------------------------------------------------------

    def test_clients_are_grouped_by_their_primary_addresss_city(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_clients_are_grouped_by_their_primary_addresss_city"""
        self._create()
        self._create(
            gst=OTHER_GST,
            company_name="Beta Seeds",
            addresses=[self._address(city=self.other_city, pincode="380001")],
        )

        response = self.client.get(GET_CLIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [group["city"]["name"] for group in response.data],
            ["Ahmedabad", "Surat"],
        )

    def test_the_list_carries_the_primary_contact_and_address(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_the_list_carries_the_primary_contact_and_address"""
        self._create()

        card = self.client.get(GET_CLIENTS_URL).data[0]["clients"][0]

        self.assertEqual(card["company_name"], "Acme Seeds")
        self.assertEqual(card["primary_contact"]["phone_number"], "9876500001")
        self.assertEqual(card["primary_address"]["pincode"], "395007")

    def test_only_my_own_clients_are_listed(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_only_my_own_clients_are_listed"""
        self._create()
        self.login_as(self.other_sales_person)

        response = self.client.get(GET_CLIENTS_URL)

        self.assertEqual(response.data, [])
        self.assertEqual(Client.objects.count(), 1)

    def test_an_admin_without_a_sales_profile_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_admin_without_a_sales_profile_is_rejected"""
        self.login_as(self.admin_user)

        self.assertEqual(self.client.get(GET_CLIENTS_URL).status_code, 403)
