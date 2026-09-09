"""Android client endpoints: get-clients, create-client and update-client.

Token-only sales-person endpoints, exercised over the ``AndroidApiTestCase``
baseline (DML-seeded, bearer-token auth).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import verify_client
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

    # 15-char GSTINs that differ only in the final char (see validate_gst_number).
    _GST_SUFFIXES = "013456789ACDEFGHIJKLMNOPQRSTUWXY"

    @classmethod
    def _gst(cls, index: int) -> str:
        """A distinct valid GSTIN for the ``index``-th throwaway client."""
        return f"27AAPFU0939F1Z{cls._GST_SUFFIXES[index]}"

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

    def _seed_clients_in_two_cities(self):
        """Acme with a Surat primary address, Beta with an Ahmedabad one."""
        self._create()
        self._create(
            gst=OTHER_GST,
            company_name="Beta Seeds",
            addresses=[self._address(city=self.other_city, pincode="380001")],
        )

    def test_no_filter_returns_the_first_page_and_the_catalogues(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_no_filter_returns_the_first_page_and_the_catalogues"""
        self._seed_clients_in_two_cities()

        response = self.client.get(GET_CLIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 2)
        self.assertEqual(
            sorted(c["company_name"] for c in response.data["results"]),
            ["Acme Seeds", "Beta Seeds"],
        )
        self.assertEqual(
            [(f["filter"], f["kind"]) for f in response.data["available_filters"]],
            [("city_id", "select"), ("status", "select"), ("created", "datetime_range")],
        )
        created = response.data["available_filters"][2]
        self.assertEqual(created["params"], ["created_gte", "created_lte"])
        self.assertEqual(
            [s["sort"] for s in response.data["available_sorts"]],
            ["created_at", "company_name"],
        )

    def test_the_city_id_filter_advertises_only_this_sales_persons_cities(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_the_city_id_filter_advertises_only_this_sales_persons_cities"""
        self._create()  # sales_person: one client in Surat
        self._create(  # other_sales_person: one client in Ahmedabad -- must not leak
            actor=self.other_sales_person,
            gst=OTHER_GST,
            company_name="Beta Seeds",
            addresses=[self._address(city=self.other_city, pincode="380001")],
        )
        self.login_as(self.sales_person)

        options = self.client.get(GET_CLIENTS_URL).data["available_filters"][0]["options"]

        self.assertEqual([o["label"] for o in options], ["Surat"])
        self.assertEqual([o["value"] for o in options], [self.city.id])

    def test_filtering_by_primary_address_city_returns_only_matching_clients(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_filtering_by_primary_address_city_returns_only_matching_clients"""
        self._seed_clients_in_two_cities()

        response = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.other_city.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 1)
        self.assertEqual(
            [c["company_name"] for c in response.data["results"]], ["Beta Seeds"]
        )

    def test_filtering_accepts_several_comma_separated_city_ids(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_filtering_accepts_several_comma_separated_city_ids"""
        self._seed_clients_in_two_cities()

        response = self.client.get(
            GET_CLIENTS_URL, {"city_id": f"{self.city.id},{self.other_city.id}"}
        )

        self.assertEqual(response.data["total_count"], 2)
        self.assertEqual(
            sorted(c["company_name"] for c in response.data["results"]),
            ["Acme Seeds", "Beta Seeds"],
        )

    def test_only_the_primary_address_city_is_matched(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_only_the_primary_address_city_is_matched"""
        self.login_as(self.sales_person)
        self.client.post(
            CREATE_CLIENT_URL,
            self._body(
                addresses=[
                    self._address(is_primary=True),
                    self._address(
                        line_1="2 Side Road", city=self.other_city, pincode="380001"
                    ),
                ]
            ),
            format="json",
        )

        matched = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.city.id)})
        missed = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.other_city.id)})

        self.assertEqual(matched.data["total_count"], 1)
        self.assertEqual(missed.data["total_count"], 0)

    def test_filtering_by_status(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_filtering_by_status"""
        self._create()  # Acme -- stays VERIFICATION_PENDING
        self._create(gst=OTHER_GST, company_name="Beta Seeds")
        verify_client(Client.objects.get(company_name="Beta Seeds"), self.admin_user)
        self.login_as(self.sales_person)

        verified = self.client.get(GET_CLIENTS_URL, {"status": "VERIFIED"})
        pending = self.client.get(GET_CLIENTS_URL, {"status": "VERIFICATION_PENDING"})

        self.assertEqual(
            [c["company_name"] for c in verified.data["results"]], ["Beta Seeds"]
        )
        self.assertEqual(
            [c["company_name"] for c in pending.data["results"]], ["Acme Seeds"]
        )
        self.assertEqual(
            [o["value"] for o in verified.data["available_filters"][1]["options"]],
            ["VERIFICATION_PENDING", "VERIFIED"],
        )

    def test_an_unknown_status_code_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_unknown_status_code_is_rejected"""
        self._create()

        response = self.client.get(GET_CLIENTS_URL, {"status": "NOPE"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown status", response.data["detail"])

    def test_filtering_by_the_created_window(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_filtering_by_created_window"""
        self._create()
        acme = Client.objects.get(company_name="Acme Seeds")
        Client.objects.filter(pk=acme.pk).update(created_at="2020-01-01T00:00:00Z")
        self._create(gst=OTHER_GST, company_name="Beta Seeds")  # created now
        self.login_as(self.sales_person)

        recent = self.client.get(GET_CLIENTS_URL, {"created_gte": "2024-01-01T00:00:00Z"})
        old = self.client.get(GET_CLIENTS_URL, {"created_lte": "2021-01-01T00:00:00Z"})

        self.assertEqual(
            [c["company_name"] for c in recent.data["results"]], ["Beta Seeds"]
        )
        self.assertEqual(
            [c["company_name"] for c in old.data["results"]], ["Acme Seeds"]
        )

    def test_an_inverted_created_window_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_inverted_created_window_is_rejected"""
        self._create()

        response = self.client.get(
            GET_CLIENTS_URL,
            {"created_gte": "2026-02-01T00:00:00Z", "created_lte": "2026-01-01T00:00:00Z"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_page_carries_the_primary_contact_and_address(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_the_page_carries_the_primary_contact_and_address"""
        self._create()

        response = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.city.id)})

        card = response.data["results"][0]
        self.assertEqual(card["company_name"], "Acme Seeds")
        self.assertEqual(card["primary_contact"]["phone_number"], "9876500001")
        self.assertEqual(card["primary_address"]["pincode"], "395007")

    def test_only_my_own_clients_are_listed(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_only_my_own_clients_are_listed"""
        self._create()
        self.login_as(self.other_sales_person)

        response = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.city.id)})

        self.assertEqual(response.data["results"], [])
        self.assertEqual(response.data["total_count"], 0)
        self.assertEqual(Client.objects.count(), 1)

    def test_default_sort_is_newest_first_and_company_name_sort_is_alphabetical(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_default_sort_is_newest_first_and_company_name_sort_is_alphabetical"""
        self.login_as(self.sales_person)
        for index, name in enumerate(("Charlie", "Alpha", "Bravo")):
            self.client.post(
                CREATE_CLIENT_URL,
                self._body(gst=self._gst(index), company_name=f"{name} Seeds"),
                format="json",
            )

        default = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.city.id)})
        by_name = self.client.get(
            GET_CLIENTS_URL, {"city_id": str(self.city.id), "sort": "company_name"}
        )

        self.assertEqual(
            [c["company_name"] for c in default.data["results"]],
            ["Bravo Seeds", "Alpha Seeds", "Charlie Seeds"],
        )
        self.assertEqual(
            [c["company_name"] for c in by_name.data["results"]],
            ["Alpha Seeds", "Bravo Seeds", "Charlie Seeds"],
        )

    def test_a_descending_sort_is_accepted(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_a_descending_sort_is_accepted"""
        self.login_as(self.sales_person)
        for index, name in enumerate(("Alpha", "Bravo")):
            self.client.post(
                CREATE_CLIENT_URL,
                self._body(gst=self._gst(index), company_name=f"{name} Seeds"),
                format="json",
            )

        response = self.client.get(
            GET_CLIENTS_URL, {"city_id": str(self.city.id), "sort": "-company_name"}
        )

        self.assertEqual(
            [c["company_name"] for c in response.data["results"]],
            ["Bravo Seeds", "Alpha Seeds"],
        )

    def test_an_unknown_sort_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_unknown_sort_is_rejected"""
        self._create()

        response = self.client.get(GET_CLIENTS_URL, {"sort": "gst_number"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown sort", response.data["detail"])

    def test_results_are_paginated(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_results_are_paginated"""
        self.login_as(self.sales_person)
        for index in range(12):
            created = self.client.post(
                CREATE_CLIENT_URL,
                self._body(gst=self._gst(index), company_name=f"Client {index:02d}"),
                format="json",
            )
            self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        page_1 = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.city.id)})
        self.assertEqual(page_1.data["total_count"], 12)
        self.assertEqual(page_1.data["total_pages"], 2)
        self.assertEqual(len(page_1.data["results"]), 10)
        self.assertEqual(page_1.data["next_page_number"], 2)
        self.assertIsNone(page_1.data["previous_page_number"])

        page_2 = self.client.get(
            GET_CLIENTS_URL, {"city_id": str(self.city.id), "page": 2}
        )
        self.assertEqual(len(page_2.data["results"]), 2)
        self.assertIsNone(page_2.data["next_page_number"])
        self.assertEqual(page_2.data["previous_page_number"], 1)

    def test_an_unrecognised_query_param_is_ignored(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_unrecognised_query_param_is_ignored"""
        self._seed_clients_in_two_cities()

        response = self.client.get(GET_CLIENTS_URL, {"company_name": "Acme"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 2)

    def test_an_empty_filter_value_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_empty_filter_value_is_rejected"""
        self._create()

        response = self.client.get(GET_CLIENTS_URL, {"city_id": ""})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("at least one value", response.data["detail"])

    def test_non_integer_filter_values_are_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_non_integer_filter_values_are_rejected"""
        self._create()

        response = self.client.get(GET_CLIENTS_URL, {"city_id": "1,not-a-number"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_an_admin_without_a_sales_profile_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_an_admin_without_a_sales_profile_is_rejected"""
        self.login_as(self.admin_user)

        self.assertEqual(self.client.get(GET_CLIENTS_URL).status_code, 403)
