"""Android independent-farmer endpoints: ``farmers`` and ``farmer/<public_id>``.

A farmer recorded outside any field trip is a ``FarmerVisit`` with no trip,
owned by the sales person who entered it. Covered here: the CRUD round trip,
``is_lead``, the per-sales-person contact rule, ownership (404, never 403) and
how such a farmer shows up on the trip-based endpoints and the admin list.
Authentication and role gating are proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient

from aggregator.models import FarmerVisit
from aggregator.models.Status import StatusIds
from tests.android.common import AndroidApiTestCase
from tests.field_trip_fixtures import FieldTripFixtures

BASE = "/android/api/v1/"
FARMERS_URL = BASE + "farmers"
FARMER_URL = BASE + "farmer/{public_id}"
CREATE_VISIT_URL = BASE + "create-farmer-visit"
EDIT_VISIT_URL = BASE + "edit-farmer-visit/{public_id}"
ADMIN_FARMERS_URL = "/api/sales-admin/farmers/"


class IndependentFarmerApiTest(FieldTripFixtures, AndroidApiTestCase):
    """tests/android/test_independent_farmers.py::IndependentFarmerApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.set_up_field_trip_fixtures()

    def setUp(self):
        super().setUp()
        self.login_as(self.sales_person)

    def _body(self, **overrides) -> dict:
        return {
            "farmer_name": " Ramesh Patel ",
            "contact_number": "9876500101",
            "village": "Kamrej",
            "land_area_bigha": "2.5000",
            "crop_ids": [self.castor.id],
            "product_public_ids": [self.castor_seed.public_id],
            **overrides,
        }

    def _create(self, **overrides) -> dict:
        response = self.client.post(FARMERS_URL, self._body(**overrides), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        return response.json()

    def test_create_records_a_farmer_with_no_trip_and_is_lead_off(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_create_records_a_farmer_with_no_trip_and_is_lead_off"""
        payload = self._create()
        self.assertEqual(payload["farmer_name"], "Ramesh Patel")
        self.assertFalse(payload["is_lead"])
        self.assertIsNone(payload["field_trip_public_id"])
        self.assertTrue(payload["uses_our_products"])
        self.assertEqual([c["id"] for c in payload["crops"]], [self.castor.id])
        farmer = FarmerVisit.objects.get(public_id=payload["public_id"])
        self.assertIsNone(farmer.field_trip)
        self.assertEqual(farmer.created_by, self.sales_person)

    def test_create_can_flag_a_lead_and_needs_a_village_and_a_crop(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_create_can_flag_a_lead_and_needs_a_village_and_a_crop"""
        self.assertTrue(self._create(is_lead=True)["is_lead"])
        for label, overrides in {
            "no village": {"village": ""},
            "missing village": {"village": None},
            "no crops": {"crop_ids": []},
            "bad phone": {"contact_number": "123"},
        }.items():
            with self.subTest(label):
                response = self.client.post(
                    FARMERS_URL,
                    {**self._body(contact_number="9876500102"), **overrides},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("detail", response.json())

    def test_a_contact_number_is_unique_per_sales_person(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_a_contact_number_is_unique_per_sales_person"""
        self._create()
        again = self.client.post(FARMERS_URL, self._body(), format="json")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

        self.login_as(self.other_sales_person)
        self._create()  # another sales person may record the same farmer

    def test_list_returns_only_my_independent_farmers(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_list_returns_only_my_independent_farmers"""
        mine = self._create()
        self._create(contact_number="9876500103", farmer_name="Suresh", is_lead=True)
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        self.client.post(
            CREATE_VISIT_URL,
            {
                "field_trip_public_id": trip.public_id,
                "farmer_name": "On Trip",
                "contact_number": "9876500104",
                "land_area_bigha": "1",
                "crop_ids": [self.castor.id],
            },
            format="json",
        )
        self.login_as(self.other_sales_person)
        self._create(contact_number="9876500105")
        self.login_as(self.sales_person)

        response = self.client.get(FARMERS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["farmer_name"] for row in response.json()["results"]}
        self.assertEqual(names, {"Ramesh Patel", "Suresh"})
        self.assertEqual(response.json()["total_count"], 2)

        leads = self.client.get(FARMERS_URL, {"is_lead": "true"}).json()["results"]
        self.assertEqual([row["farmer_name"] for row in leads], ["Suresh"])
        by_id = self.client.get(FARMERS_URL, {"public_id": mine["public_id"]}).json()["results"]
        self.assertEqual([row["public_id"] for row in by_id], [mine["public_id"]])

    def test_detail_and_ownership(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_detail_and_ownership"""
        farmer = self._create()
        url = FARMER_URL.format(public_id=farmer["public_id"])
        self.assertEqual(self.client.get(url).json()["public_id"], farmer["public_id"])

        self.login_as(self.other_sales_person)
        for method in (self.client.get, self.client.patch, self.client.delete):
            with self.subTest(method=method.__name__):
                self.assertEqual(method(url).status_code, status.HTTP_404_NOT_FOUND)

    def test_a_trip_visit_is_not_reachable_through_the_farmer_endpoints(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_a_trip_visit_is_not_reachable_through_the_farmer_endpoints"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        visit = self.make_visit(trip)
        response = self.client.get(FARMER_URL.format(public_id=visit.public_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_edits_fields_links_and_the_lead_flag(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_patch_edits_fields_links_and_the_lead_flag"""
        farmer = self._create()
        url = FARMER_URL.format(public_id=farmer["public_id"])
        response = self.client.patch(
            url,
            {
                "is_lead": True,
                "village": "Olpad",
                "crop_ids": [self.bajari.id],
                "product_public_ids": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        payload = response.json()
        self.assertTrue(payload["is_lead"])
        self.assertEqual(payload["village"], "Olpad")
        self.assertEqual([c["id"] for c in payload["crops"]], [self.bajari.id])
        self.assertFalse(payload["uses_our_products"])

        self.assertEqual(self.client.patch(url, {}, format="json").status_code, 400)
        blank = self.client.patch(url, {"farmer_name": ""}, format="json")
        self.assertEqual(blank.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_refuses_a_contact_number_already_recorded(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_patch_refuses_a_contact_number_already_recorded"""
        self._create()
        other = self._create(contact_number="9876500106")
        response = self.client.patch(
            FARMER_URL.format(public_id=other["public_id"]),
            {"contact_number": "9876500101"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_soft_deletes_and_frees_the_contact_number(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_delete_soft_deletes_and_frees_the_contact_number"""
        farmer = self._create()
        url = FARMER_URL.format(public_id=farmer["public_id"])
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(FarmerVisit.all_objects.get(public_id=farmer["public_id"]).is_deleted)
        self.assertEqual(self.client.get(FARMERS_URL).json()["total_count"], 0)
        self._create()  # the same contact can be recorded again

    def test_is_lead_is_accepted_on_trip_visits_too(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_is_lead_is_accepted_on_trip_visits_too"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        created = self.client.post(
            CREATE_VISIT_URL,
            {
                "field_trip_public_id": trip.public_id,
                "farmer_name": "On Trip",
                "contact_number": "9876500107",
                "land_area_bigha": "1",
                "crop_ids": [self.castor.id],
                "is_lead": True,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        self.assertTrue(created.json()["is_lead"])
        self.assertEqual(created.json()["field_trip_public_id"], trip.public_id)
        edited = self.client.patch(
            EDIT_VISIT_URL.format(public_id=created.json()["public_id"]),
            {"is_lead": False},
            format="json",
        )
        self.assertEqual(edited.status_code, status.HTTP_200_OK, edited.content)
        self.assertFalse(edited.json()["is_lead"])

    def test_the_admin_farmer_list_includes_a_farmer_without_a_trip(self):
        """tests/android/test_independent_farmers.py::IndependentFarmerApiTest::test_the_admin_farmer_list_includes_a_farmer_without_a_trip"""
        self._create(is_lead=True)
        admin_client = APIClient()
        admin_client.force_login(self.admin_user)
        response = admin_client.get(ADMIN_FARMERS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        row = response.json()["results"][0]
        self.assertIsNone(row["city"])
        self.assertTrue(row["is_lead"])
        self.assertIsNone(row["visits"][0]["field_trip_public_id"])
