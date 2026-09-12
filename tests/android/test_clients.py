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
CLIENT_URL = "/android/api/v1/client/{public_id}"
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

    def test_a_city_that_is_not_in_the_selected_state_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_a_city_that_is_not_in_the_selected_state_is_rejected"""
        rajasthan_city = City.objects.get(name="Jaipur")  # in Rajasthan, not Gujarat
        body = self._body(
            addresses=[self._address(city=rajasthan_city, pincode="302001")]
        )
        # _address() defaults state to Gujarat -> inconsistent with Jaipur
        self.login_as(self.sales_person)

        response = self.client.post(CREATE_CLIENT_URL, body, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Jaipur", response.data["detail"])
        self.assertIn("Gujarat", response.data["detail"])

    def test_a_mismatched_state_on_update_is_rejected(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_a_mismatched_state_on_update_is_rejected"""
        from aggregator.models import State

        created = self._create()  # address: 1 Ring Road, Surat, Gujarat
        rajasthan = State.objects.get(name="Rajasthan")

        response = self.client.post(
            UPDATE_CLIENT_URL,
            {
                "public_id": created.data["public_id"],
                # same line / pincode / city as the stored address, wrong state
                "addresses": [self._address(state=rajasthan.id)],
                "contacts": [{"name": "Ramesh", "phone_number": "9876500001"}],
                "transport_agencies": [{"name": "ABC Transport"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        client = Client.objects.get(public_id=created.data["public_id"])
        self.assertEqual(client.client_addresses.get().address.state.name, "Gujarat")

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
        """The page shape, the declared filters and sorts, and the card contents.

        tests/android/test_clients.py::AndroidClientApiTest::test_no_filter_returns_the_first_page_and_the_catalogues
        """
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
            [
                ("city_id", "select"),
                ("status", "select"),
                ("company_name", "text"),
                ("address", "text"),
                ("created", "datetime_range"),
            ],
        )
        created = next(
            f for f in response.data["available_filters"] if f["filter"] == "created"
        )
        self.assertEqual(created["params"], ["created_gte", "created_lte"])
        self.assertEqual(
            [s["sort"] for s in response.data["available_sorts"]],
            ["created_at", "company_name"],
        )

        # Each card carries the client's primary contact and primary address.
        card = next(c for c in response.data["results"] if c["company_name"] == "Acme Seeds")
        self.assertEqual(card["primary_contact"]["phone_number"], "9876500001")
        self.assertEqual(card["primary_address"]["pincode"], "395007")

    def test_the_list_is_scoped_to_the_calling_sales_person(self):
        """Another sales person's clients are neither listed nor advertised in the
        city catalogue, even though the rows exist.

        tests/android/test_clients.py::AndroidClientApiTest::test_the_list_is_scoped_to_the_calling_sales_person
        """
        self._create()  # sales_person: one client in Surat
        self._create(  # other_sales_person: one client in Ahmedabad
            actor=self.other_sales_person,
            gst=OTHER_GST,
            company_name="Beta Seeds",
            addresses=[self._address(city=self.other_city, pincode="380001")],
        )

        self.login_as(self.sales_person)
        mine = self.client.get(GET_CLIENTS_URL)
        self.assertEqual(
            [c["company_name"] for c in mine.data["results"]], ["Acme Seeds"]
        )
        # The city catalogue must not leak Ahmedabad, where only the other
        # sales person has a client.
        options = mine.data["available_filters"][0]["options"]
        self.assertEqual([o["label"] for o in options], ["Surat"])
        self.assertEqual([o["value"] for o in options], [self.city.id])

        # Filtering by a city only the other sales person serves finds nothing.
        theirs = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.other_city.id)})
        self.assertEqual(theirs.data["results"], [])
        self.assertEqual(theirs.data["total_count"], 0)
        self.assertEqual(Client.objects.count(), 2)

    def test_the_city_filter_matches_only_the_primary_address(self):
        """One id, several comma-separated ids, and the primary-only rule.

        tests/android/test_clients.py::AndroidClientApiTest::test_the_city_filter_matches_only_the_primary_address
        """
        self._seed_clients_in_two_cities()

        one = self.client.get(GET_CLIENTS_URL, {"city_id": str(self.other_city.id)})
        self.assertEqual(one.status_code, status.HTTP_200_OK)
        self.assertEqual([c["company_name"] for c in one.data["results"]], ["Beta Seeds"])

        both = self.client.get(
            GET_CLIENTS_URL, {"city_id": f"{self.city.id},{self.other_city.id}"}
        )
        self.assertEqual(both.data["total_count"], 2)
        self.assertEqual(
            sorted(c["company_name"] for c in both.data["results"]),
            ["Acme Seeds", "Beta Seeds"],
        )

        # A client whose *secondary* address is in Ahmedabad is not matched by it.
        self.client.post(
            CREATE_CLIENT_URL,
            self._body(
                gst=self._gst(2),
                company_name="Gamma Seeds",
                addresses=[
                    self._address(is_primary=True),
                    self._address(
                        line_1="2 Side Road", city=self.other_city, pincode="380001"
                    ),
                ],
            ),
            format="json",
        )
        by_secondary = self.client.get(
            GET_CLIENTS_URL, {"city_id": str(self.other_city.id)}
        )
        self.assertNotIn(
            "Gamma Seeds", [c["company_name"] for c in by_secondary.data["results"]]
        )

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

        # A code outside the catalogue is a 400, not an empty page.
        unknown = self.client.get(GET_CLIENTS_URL, {"status": "NOPE"})
        self.assertEqual(unknown.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown status", unknown.data["detail"])

    def test_filtering_by_the_created_window(self):
        """Each bound narrows the page on its own; an inverted window is a 400.

        tests/android/test_clients.py::AndroidClientApiTest::test_filtering_by_the_created_window
        """
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

        inverted = self.client.get(
            GET_CLIENTS_URL,
            {"created_gte": "2026-02-01T00:00:00Z", "created_lte": "2026-01-01T00:00:00Z"},
        )
        self.assertEqual(inverted.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_text_filters_match_the_name_and_the_primary_address(self):
        """``company_name`` and ``address`` each match a substring, ignore
        non-primary addresses, AND together, and refuse a blank value.

        tests/android/test_clients.py::AndroidClientApiTest::test_the_text_filters_match_the_name_and_the_primary_address
        """
        # Acme Seeds: 1 Ring Road, Surat 395007 (primary) + a Dockside secondary.
        self.login_as(self.sales_person)
        self.client.post(
            CREATE_CLIENT_URL,
            self._body(
                addresses=[
                    self._address(line_1="1 Ring Road", is_primary=True),
                    self._address(line_1="9 Dockside Lane", pincode="395011"),
                ]
            ),
            format="json",
        )
        # Acme Traders: 7 Harbour Street, Ahmedabad 380001 (primary).
        self._create(
            gst=OTHER_GST,
            company_name="Acme Traders",
            addresses=[
                self._address(line_1="7 Harbour Street", city=self.other_city, pincode="380001")
            ],
        )
        self.login_as(self.sales_person)

        cases = [
            ("company_name substring", {"company_name": "cme se"}, ["Acme Seeds"]),
            ("company_name miss", {"company_name": "nonesuch"}, []),
            ("address street", {"address": "harbour"}, ["Acme Traders"]),
            ("address city", {"address": "surat"}, ["Acme Seeds"]),
            ("address pincode", {"address": "3800"}, ["Acme Traders"]),
            # The Dockside address is not primary, so it is never matched.
            ("address ignores non-primary", {"address": "dockside"}, []),
            # Both filters AND together rather than widening the page.
            (
                "name and address together",
                {"company_name": "acme", "address": "ahmedabad"},
                ["Acme Traders"],
            ),
        ]
        for label, query, expected in cases:
            with self.subTest(filter=label):
                response = self.client.get(GET_CLIENTS_URL, query)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    [c["company_name"] for c in response.data["results"]], expected
                )

        self.assertEqual(
            next(
                f["kind"]
                for f in self.client.get(GET_CLIENTS_URL).data["available_filters"]
                if f["filter"] == "company_name"
            ),
            "text",
        )
        # A whitespace-only value is a mistake, not "no filter".
        blank = self.client.get(GET_CLIENTS_URL, {"company_name": "   "})
        self.assertEqual(blank.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_filter_values_are_rejected_and_unknown_params_ignored(self):
        """tests/android/test_clients.py::AndroidClientApiTest::test_malformed_filter_values_are_rejected_and_unknown_params_ignored"""
        self._seed_clients_in_two_cities()

        empty = self.client.get(GET_CLIENTS_URL, {"city_id": ""})
        self.assertEqual(empty.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("at least one value", empty.data["detail"])

        non_integer = self.client.get(GET_CLIENTS_URL, {"city_id": "1,not-a-number"})
        self.assertEqual(non_integer.status_code, status.HTTP_400_BAD_REQUEST)

        # A param the view does not declare is ignored rather than rejected, so
        # an older client's extra query string keeps working.
        ignored = self.client.get(GET_CLIENTS_URL, {"gst_number": "27AAPFU"})
        self.assertEqual(ignored.status_code, status.HTTP_200_OK)
        self.assertEqual(ignored.data["total_count"], 2)

    def test_sorting(self):
        """Newest first by default, ``company_name`` ascending and descending, and
        a 400 for a column that is not a declared sort.

        tests/android/test_clients.py::AndroidClientApiTest::test_sorting
        """
        self.login_as(self.sales_person)
        for index, name in enumerate(("Charlie", "Alpha", "Bravo")):
            self.client.post(
                CREATE_CLIENT_URL,
                self._body(gst=self._gst(index), company_name=f"{name} Seeds"),
                format="json",
            )

        city = {"city_id": str(self.city.id)}
        cases = [
            ("default (newest first)", city, ["Bravo Seeds", "Alpha Seeds", "Charlie Seeds"]),
            (
                "company_name ascending",
                {**city, "sort": "company_name"},
                ["Alpha Seeds", "Bravo Seeds", "Charlie Seeds"],
            ),
            (
                "company_name descending",
                {**city, "sort": "-company_name"},
                ["Charlie Seeds", "Bravo Seeds", "Alpha Seeds"],
            ),
        ]
        for label, query, expected in cases:
            with self.subTest(sort=label):
                response = self.client.get(GET_CLIENTS_URL, query)
                self.assertEqual(
                    [c["company_name"] for c in response.data["results"]], expected
                )

        unknown = self.client.get(GET_CLIENTS_URL, {"sort": "gst_number"})
        self.assertEqual(unknown.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown sort", unknown.data["detail"])

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

    # -- single client detail -----------------------------------------------

    def test_client_detail_returns_core_data_and_every_list(self):
        """The full record before and after a sales admin verifies it.

        tests/android/test_clients.py::AndroidClientApiTest::test_client_detail_returns_core_data_and_every_list
        """
        created = self._create(
            addresses=[
                self._address(is_primary=True, label="HQ"),
                self._address(line_1="2 Side Road", pincode="395010"),
            ],
            contacts=[
                {"name": "Ramesh", "phone_number": "9876500001", "is_primary": True},
                {"name": "Suresh", "phone_number": "9876500002", "role": "Accounts"},
            ],
            transport_agencies=[{"name": "ABC Transport"}, {"name": "XYZ Logistics"}],
        )
        public_id = created.data["public_id"]

        response = self.client.get(CLIENT_URL.format(public_id=public_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.data
        self.assertEqual(body["public_id"], public_id)
        self.assertEqual(body["company_name"], "Acme Seeds")
        self.assertEqual(body["gst_number"], GST)
        self.assertEqual(body["status"], "VERIFICATION_PENDING")
        self.assertFalse(body["is_verified"])
        self.assertEqual({a["line_1"] for a in body["addresses"]}, {"1 Ring Road", "2 Side Road"})
        self.assertEqual(sum(a["is_primary"] for a in body["addresses"]), 1)
        self.assertEqual({c["name"] for c in body["contacts"]}, {"Ramesh", "Suresh"})
        self.assertEqual(
            {t["name"] for t in body["transport_agencies"]},
            {"ABC Transport", "XYZ Logistics"},
        )

        # Once a sales admin verifies it, the same record reflects that.
        verify_client(Client.objects.get(public_id=public_id), self.admin_user)
        body = self.client.get(CLIENT_URL.format(public_id=public_id)).data
        self.assertEqual(body["status"], "VERIFIED")
        self.assertTrue(body["is_verified"])
        self.assertEqual(body["verified_by"], self.admin_user.name)
        self.assertIsNotNone(body["verified_at"])

    def test_client_detail_is_404_for_anything_the_caller_does_not_own(self):
        """An unknown id and another sales person's client are indistinguishable.

        tests/android/test_clients.py::AndroidClientApiTest::test_client_detail_is_404_for_anything_the_caller_does_not_own
        """
        public_id = self._create().data["public_id"]

        self.login_as(self.sales_person)
        self.assertEqual(
            self.client.get(CLIENT_URL.format(public_id="C-DOESNOTEXIST")).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.login_as(self.other_sales_person)
        self.assertEqual(
            self.client.get(CLIENT_URL.format(public_id=public_id)).status_code,
            status.HTTP_404_NOT_FOUND,
        )
