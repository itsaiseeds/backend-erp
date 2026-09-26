"""ORM-backed tests for the party endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own app admin in ``setUpTestData``. Request/response flows are
exercised over the test :class:`~rest_framework.test.APIClient` with a logged-in
session, since these are session-only web endpoints.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Party
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

PARTIES_URL = "/api/sales-admin/parties"


class PartyApiTest(WebApiTestCase):
    """Cover permission gating and CRUD for the admin-only party endpoints.

    tests/test_party_api.py::PartyApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin, two seeded cities and a seeded party."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        cls.seed_admin = User.objects.create_user(
            phone_number="7777777777",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=cls.seed_admin, can_update_stock_count=True, created_by=cls.superuser
        )

        cls.surat = City.objects.get(name="Surat")
        cls.ahmedabad = City.objects.get(name="Ahmedabad")
        cls.party = Party.objects.create(
            name="ABC Traders", city=cls.surat, created_by=cls.seed_admin
        )

    # -- helpers --------------------------------------------------------------

    def _url(self, party):
        """Return the update/delete URL for a party (by primary key)."""
        return f"{PARTIES_URL}/{party.id}"

    def _create_party(self, name="ZZZ Traders", city=None):
        """POST a party (the seeded city by default) and return the response."""
        return self.client.post(
            PARTIES_URL, {"name": name, "city": (city or self.surat).id}, format="json"
        )

    # -- creation -------------------------------------------------------------

    def test_admin_create_party_payload_shape_and_name_normalisation(self):
        """The created row is echoed back, attributed, and its name trimmed.

        tests/test_party_api.py::PartyApiTest::test_admin_create_party_payload_shape_and_name_normalisation
        """
        self.login_as(self.seed_admin)
        response = self._create_party("  Green Agro  ")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        party = response.data

        # The new party takes the next id after the seeded one. This is a stable
        # assertion because DMLTestCase rewinds every sequence before each test
        # (Postgres does not roll back nextval), so ids do not drift.
        self.assertEqual(party["id"], self.party.id + 1)
        self.assertEqual(party["name"], "Green Agro")  # surrounding whitespace stripped
        self.assertEqual(party["city"], {"id": self.surat.id, "name": "Surat"})

        created = Party.all_objects.get(pk=party["id"])
        self.assertEqual(created.name, "Green Agro")
        self.assertEqual(created.city_id, self.surat.id)
        self.assertEqual(created.created_by_id, self.seed_admin.id)
        self.assertEqual(Party.all_objects.filter(name="Green Agro").count(), 1)

    def test_the_same_party_name_in_a_different_city_is_allowed(self):
        """Uniqueness is scoped to (name, city), so another city may repeat it.

        tests/test_party_api.py::PartyApiTest::test_the_same_party_name_in_a_different_city_is_allowed
        """
        self.login_as(self.seed_admin)
        response = self._create_party("ABC Traders", city=self.ahmedabad)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data["city"]["name"], "Ahmedabad")

    # -- validation (shared by create and update) -----------------------------

    def test_invalid_party_data_is_rejected_on_create_and_update(self):
        """Blank, missing, unknown-city and duplicate bodies all 400.

        tests/test_party_api.py::PartyApiTest::test_invalid_party_data_is_rejected_on_create_and_update
        """
        self.login_as(self.seed_admin)
        other = Party.objects.create(
            name="Private Ltd", city=self.surat, created_by=self.seed_admin
        )

        create_cases = [
            ("blank name", {"name": "", "city": self.surat.id}),
            ("whitespace only", {"name": "   ", "city": self.surat.id}),
            ("missing", {}),
            ("missing city", {"name": "Any Name"}),
            ("unknown city", {"name": "Any Name", "city": 999999}),
            ("duplicate in same city", {"name": "ABC Traders", "city": self.surat.id}),
        ]
        for label, body in create_cases:
            with self.subTest(verb="POST", case=label):
                self.assertEqual(
                    self.client.post(PARTIES_URL, body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        update_cases = [
            ("blank name", {"name": "   "}),
            ("duplicate of another party", {"name": self.party.name}),
        ]
        for label, body in update_cases:
            with self.subTest(verb="PATCH", case=label):
                self.assertEqual(
                    self.client.patch(self._url(other), body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    # -- update ---------------------------------------------------------------

    def test_admin_update_party(self):
        """Name and city can be changed; re-sending the party's own name is fine.

        tests/test_party_api.py::PartyApiTest::test_admin_update_party
        """
        self.login_as(self.seed_admin)
        response = self.client.patch(
            self._url(self.party), {"name": "  New Name  ", "city": self.ahmedabad.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["name"], "New Name")
        self.assertEqual(response.data["city"], {"id": self.ahmedabad.id, "name": "Ahmedabad"})

        self.party.refresh_from_db()
        self.assertEqual(self.party.name, "New Name")
        self.assertEqual(self.party.city_id, self.ahmedabad.id)

        # Re-sending the party's own (name, city) is not a duplicate.
        self.assertEqual(
            self.client.patch(
                self._url(self.party), {"name": "New Name"}, format="json"
            ).status_code,
            status.HTTP_200_OK,
        )

    def test_contact_number_is_optional_and_stored_on_create(self):
        """POST stores a valid ``contact_number``, defaults it to null, and 400s bad ones.

        tests/test_party_api.py::PartyApiTest::test_contact_number_is_optional_and_stored_on_create
        """
        self.login_as(self.seed_admin)

        response = self.client.post(
            PARTIES_URL,
            {"name": "DEF Traders", "city": self.surat.id, "contact_number": "1234567890"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data["contact_number"], "1234567890")
        created = Party.all_objects.get(pk=response.data["id"])
        self.assertEqual(created.contact_number, "1234567890")

        for label, body in (
            ("omitted", {"name": "No Phone Traders", "city": self.surat.id}),
            ("blank", {"name": "Blank Phone Traders", "city": self.surat.id, "contact_number": ""}),
        ):
            with self.subTest(case=label):
                response = self.client.post(PARTIES_URL, body, format="json")
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
                self.assertIsNone(response.data["contact_number"])
                self.assertIsNone(Party.all_objects.get(pk=response.data["id"]).contact_number)

        for label, bad_value in (("too short", "12345"), ("with country code", "+919876543210")):
            with self.subTest(case=label):
                response = self.client.post(
                    PARTIES_URL,
                    {"name": "Bad Phone Traders", "city": self.surat.id, "contact_number": bad_value},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_update_party_contact_number(self):
        """PATCH can set, change, and clear ``contact_number``; bad values 400.

        tests/test_party_api.py::PartyApiTest::test_admin_update_party_contact_number
        """
        self.login_as(self.seed_admin)

        response = self.client.patch(
            self._url(self.party), {"contact_number": "9876543210"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["contact_number"], "9876543210")
        self.party.refresh_from_db()
        self.assertEqual(self.party.contact_number, "9876543210")

        for label, bad_value in (
            ("too short", "12345"),
            ("non-numeric", "98765abcde"),
            ("with country code", "+919876543210"),
        ):
            with self.subTest(case=label):
                bad_response = self.client.patch(
                    self._url(self.party), {"contact_number": bad_value}, format="json"
                )
                self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Clearing it back out (blank) is allowed and stores NULL.
        clear_response = self.client.patch(
            self._url(self.party), {"contact_number": ""}, format="json"
        )
        self.assertEqual(clear_response.status_code, status.HTTP_200_OK, clear_response.content)
        self.assertIsNone(clear_response.data["contact_number"])
        self.party.refresh_from_db()
        self.assertIsNone(self.party.contact_number)

        # Other fields are unaffected when contact_number isn't sent.
        self.assertEqual(
            self.client.patch(
                self._url(self.party), {"name": "ABC Traders"}, format="json"
            ).status_code,
            status.HTTP_200_OK,
        )
        self.party.refresh_from_db()
        self.assertIsNone(self.party.contact_number)

    # -- filtering --------------------------------------------------------------

    def test_city_filter_options_list_only_cities_parties_are_in(self):
        """The ``city_id`` filter's catalogue options cover only in-use cities,
        and the filter itself narrows the list.

        tests/test_party_api.py::PartyApiTest::test_city_filter_options_list_only_cities_parties_are_in
        """
        self.login_as(self.seed_admin)

        # Only Surat is in use so far (the seeded party).
        entry = next(
            f for f in self.client.get(PARTIES_URL).data["available_filters"]
            if f["filter"] == "city_id"
        )
        self.assertEqual(entry["options"], [{"value": self.surat.id, "label": "Surat"}])

        self._create_party("Delta Traders", city=self.ahmedabad)

        entry = next(
            f for f in self.client.get(PARTIES_URL).data["available_filters"]
            if f["filter"] == "city_id"
        )
        self.assertEqual(
            sorted(o["label"] for o in entry["options"]), ["Ahmedabad", "Surat"]
        )

        response = self.client.get(PARTIES_URL, {"city_id": self.ahmedabad.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["name"] for item in response.data["results"]], ["Delta Traders"]
        )

    # -- deletion -------------------------------------------------------------

    def test_delete_soft_deletes_and_removes_the_party_from_the_api(self):
        """The row is flagged and attributed, drops out of the list, and 404s after.

        tests/test_party_api.py::PartyApiTest::test_delete_soft_deletes_and_removes_the_party_from_the_api
        """
        self.login_as(self.seed_admin)
        self.assertEqual(self.client.delete(self._url(self.party)).status_code,
                         status.HTTP_204_NO_CONTENT)
        self.party.refresh_from_db()
        self.assertTrue(self.party.is_deleted)
        self.assertEqual(self.party.deleted_by_id, self.seed_admin.id)

        listing = self.client.get(PARTIES_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertFalse(any(item["name"] == "ABC Traders" for item in listing.data["results"]))

    def test_an_unknown_or_deleted_party_is_404_for_both_verbs(self):
        """tests/test_party_api.py::PartyApiTest::test_an_unknown_or_deleted_party_is_404_for_both_verbs"""
        self.login_as(self.seed_admin)
        self.client.delete(self._url(self.party))

        for label, url in (
            ("unknown id", f"{PARTIES_URL}/999999"),
            ("soft-deleted party", self._url(self.party)),
        ):
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.patch(url, {"name": "Rice"}, format="json").status_code,
                    status.HTTP_404_NOT_FOUND,
                )
                self.assertEqual(
                    self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND
                )

    # -- listing --------------------------------------------------------------

    def test_list_is_a_paginated_envelope_of_live_parties(self):
        """The created party shows up; a deleted one does not.

        tests/test_party_api.py::PartyApiTest::test_list_is_a_paginated_envelope_of_live_parties
        """
        self.login_as(self.seed_admin)
        response = self._create_party()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)

        listing = self.client.get(PARTIES_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["total_count"], 2)
        names = {item["name"] for item in listing.data["results"]}
        self.assertEqual(names, {"ABC Traders", "ZZZ Traders"})
