"""Android field-trip endpoints and the crop / product utilities.

Covers planning, listing, editing, starting, ending and deleting the caller's
own trips, recording farmer visits, and the two unpaginated pickers. The status
rules themselves are proven in ``tests/test_field_trip_operations.py``; what is
asserted here is the endpoints' wiring -- above all that a sales person can
never reach another sales person's trip (404, not 403).
Authentication and role gating are proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta

from rest_framework import status

from aggregator.models import Crop, FarmerVisit, FieldTrip, Product
from aggregator.models.Status import StatusIds
from common.models import indian_now
from tests.android.common import AndroidApiTestCase
from tests.field_trip_fixtures import FieldTripFixtures

BASE = "/android/api/v1/"
CREATE_URL = BASE + "create-field-trip"
LIST_URL = BASE + "get-field-trips"
EDIT_URL = BASE + "edit-field-trip/{public_id}"
START_URL = BASE + "start-field-trip/{public_id}"
END_URL = BASE + "end-field-trip/{public_id}"
DELETE_URL = BASE + "delete-field-trip/{public_id}"
VISITS_URL = BASE + "field-trip-farmer-visits/{public_id}"
CREATE_VISIT_URL = BASE + "create-farmer-visit"
EDIT_VISIT_URL = BASE + "edit-farmer-visit/{public_id}"
CROPS_URL = BASE + "utilities/crops"
PRODUCTS_URL = BASE + "utilities/products"


class AndroidFieldTripApiTest(FieldTripFixtures, AndroidApiTestCase):
    """tests/android/test_field_trips.py::AndroidFieldTripApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.set_up_field_trip_fixtures()

    def setUp(self):
        super().setUp()
        self.login_as(self.sales_person)

    def _visit_body(self, trip, **overrides):
        return {
            "field_trip_public_id": trip.public_id,
            "farmer_name": " Ramesh Patel ",
            "contact_number": "9876500001",
            "land_area_bigha": "3.1250",
            "crop_ids": [self.castor.id, self.bajari.id],
            "product_public_ids": [self.castor_seed.public_id],
            **overrides,
        }

    def test_create_plans_a_trip_for_the_caller(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_create_plans_a_trip_for_the_caller"""
        start = indian_now() + timedelta(days=1)
        body = {
            "city_id": self.city.id,
            "village": " Kamrej ",
            "expected_start_at": start.isoformat(),
            "expected_end_at": (start + timedelta(hours=6)).isoformat(),
        }
        response = self.client.post(CREATE_URL, body, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()
        self.assertEqual(payload["status"], "PLANNED")
        self.assertEqual(payload["village"], "Kamrej")
        self.assertEqual(payload["farmer_visit_count"], 0)
        trip = FieldTrip.objects.get(public_id=payload["public_id"])
        self.assertEqual(trip.created_by, self.sales_person)

        bad_cases = {
            "end before start": {**body, "expected_end_at": body["expected_start_at"]},
            "unknown city": {**body, "city_id": 999999},
            "missing village": {k: v for k, v in body.items() if k != "village"},
        }
        for name, bad in bad_cases.items():
            with self.subTest(case=name):
                response = self.client.post(CREATE_URL, bad, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_shows_only_the_callers_trips(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_list_shows_only_the_callers_trips"""
        mine = self.make_trip()
        approved = self.make_trip(status=StatusIds.APPROVED, city=self.other_city, starts_in_days=2)
        self.make_trip(owner=self.other_sales_person, city=self.other_city)

        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["public_id"] for row in response.json()["results"]]
        self.assertEqual(ids, [approved.public_id, mine.public_id])
        filters = {entry["filter"] for entry in response.json()["available_filters"]}
        self.assertNotIn("created_by", filters)

        response = self.client.get(LIST_URL, {"status": "APPROVED"})
        self.assertEqual(
            [row["public_id"] for row in response.json()["results"]], [approved.public_id]
        )

    def test_another_sales_persons_trip_is_not_found(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_another_sales_persons_trip_is_not_found"""
        theirs = self.make_trip(owner=self.other_sales_person, status=StatusIds.IN_PROGRESS)
        public_id = theirs.public_id
        requests = {
            "edit": lambda: self.client.patch(
                EDIT_URL.format(public_id=public_id), {"village": "X"}, format="json"
            ),
            "start": lambda: self.client.post(START_URL.format(public_id=public_id)),
            "end": lambda: self.client.post(END_URL.format(public_id=public_id)),
            "delete": lambda: self.client.delete(DELETE_URL.format(public_id=public_id)),
            "visits": lambda: self.client.get(VISITS_URL.format(public_id=public_id)),
            "create visit": lambda: self.client.post(
                CREATE_VISIT_URL, self._visit_body(theirs), format="json"
            ),
        }
        for name, request in requests.items():
            with self.subTest(request=name):
                self.assertEqual(request().status_code, status.HTTP_404_NOT_FOUND)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status_code, "IN_PROGRESS")
        self.assertFalse(FarmerVisit.objects.filter(field_trip=theirs).exists())

    def test_editing_an_approved_trip_sends_it_back_for_approval(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_editing_an_approved_trip_sends_it_back_for_approval"""
        trip = self.make_trip(status=StatusIds.APPROVED)
        response = self.client.patch(
            EDIT_URL.format(public_id=trip.public_id), {"village": "Bardoli"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "PLANNED")
        self.assertEqual(response.json()["village"], "Bardoli")
        self.assertIsNone(response.json()["approved_by"])

        started = self.make_trip(status=StatusIds.IN_PROGRESS)
        response = self.client.patch(
            EDIT_URL.format(public_id=started.public_id), {"village": "X"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_and_end_stamp_server_time(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_start_and_end_stamp_server_time"""
        planned = self.make_trip()
        refused = self.client.post(START_URL.format(public_id=planned.public_id))
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)

        trip = self.make_trip(status=StatusIds.APPROVED)
        response = self.client.post(START_URL.format(public_id=trip.public_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "IN_PROGRESS")
        self.assertIsNotNone(response.json()["started_at"])

        second = self.make_trip(status=StatusIds.APPROVED)
        busy = self.client.post(START_URL.format(public_id=second.public_id))
        self.assertEqual(busy.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(trip.public_id, busy.json()["detail"])

        response = self.client.post(END_URL.format(public_id=trip.public_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "COMPLETED")
        self.assertIsNotNone(response.json()["ended_at"])

    def test_delete_only_before_the_trip_starts(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_delete_only_before_the_trip_starts"""
        planned = self.make_trip()
        response = self.client.delete(DELETE_URL.format(public_id=planned.public_id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FieldTrip.objects.filter(id=planned.id).exists())

        completed = self.make_trip(status=StatusIds.COMPLETED)
        response = self.client.delete(DELETE_URL.format(public_id=completed.public_id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_farmer_visit(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_create_farmer_visit"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        response = self.client.post(CREATE_VISIT_URL, self._visit_body(trip), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()
        self.assertEqual(payload["farmer_name"], "Ramesh Patel")
        self.assertEqual(payload["village"], "Kamrej")
        self.assertEqual(payload["land_area_bigha"], "3.1250")
        self.assertEqual(len(payload["crops"]), 2)
        self.assertTrue(payload["uses_our_products"])

        listed = self.client.get(VISITS_URL.format(public_id=trip.public_id))
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [row["public_id"] for row in listed.json()["results"]], [payload["public_id"]]
        )

        no_products = self._visit_body(
            trip, contact_number="9876500002", village="Velanja", product_public_ids=[]
        )
        response = self.client.post(CREATE_VISIT_URL, no_products, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["village"], "Velanja")
        self.assertFalse(response.json()["uses_our_products"])

        bad_cases = {
            "no crops": {"crop_ids": []},
            "unknown crop": {"crop_ids": [999999]},
            "unknown product": {"product_public_ids": ["P-NOPE"]},
            "bad phone": {"contact_number": "+919876500009"},
            "duplicate phone": {"contact_number": "9876500001"},
            "negative land": {"land_area_bigha": "-2"},
        }
        for name, overrides in bad_cases.items():
            with self.subTest(case=name):
                body = self._visit_body(trip, contact_number="9876500003")
                body.update(overrides)
                response = self.client.post(CREATE_VISIT_URL, body, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.post(END_URL.format(public_id=trip.public_id))
        late = self._visit_body(trip, contact_number="9876500004")
        response = self.client.post(CREATE_VISIT_URL, late, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_edit_farmer_visit_renames_only_while_the_trip_is_in_progress(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_edit_farmer_visit_renames_only_while_the_trip_is_in_progress"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        visit = self.make_visit(trip)
        url = EDIT_VISIT_URL.format(public_id=visit.public_id)

        response = self.client.patch(
            url, {"farmer_name": " Suresh Patel ", "field_trip_public_id": "FT-OTHER"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["farmer_name"], "Suresh Patel")
        visit.refresh_from_db()
        self.assertEqual(visit.contact_number, "9876500001")
        self.assertEqual(visit.field_trip_id, trip.pk)

        blank = self.client.patch(url, {"farmer_name": "  "}, format="json")
        self.assertEqual(blank.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.post(END_URL.format(public_id=trip.public_id))
        late = self.client.patch(url, {"farmer_name": "Late"}, format="json")
        self.assertEqual(late.status_code, status.HTTP_400_BAD_REQUEST)
        visit.refresh_from_db()
        self.assertEqual(visit.farmer_name, "Suresh Patel")

    def test_edit_farmer_visit_is_partial_and_required_fields_stay_filled(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_edit_farmer_visit_is_partial_and_required_fields_stay_filled"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        visit = self.make_visit(trip)
        url = EDIT_VISIT_URL.format(public_id=visit.public_id)

        crops_only = self.client.patch(url, {"crop_ids": [self.bajari.id]}, format="json")
        self.assertEqual(crops_only.status_code, status.HTTP_200_OK)
        body = crops_only.json()
        self.assertEqual(body["farmer_name"], "Ramesh Patel")
        self.assertEqual([c["id"] for c in body["crops"]], [self.bajari.id])

        no_products = self.client.patch(url, {"product_public_ids": []}, format="json")
        self.assertEqual(no_products.status_code, status.HTTP_200_OK)
        self.assertEqual(no_products.json()["products"], [])
        self.assertEqual([c["id"] for c in no_products.json()["crops"]], [self.bajari.id])

        restored = self.client.patch(
            url, {"crop_ids": [self.castor.id, self.bajari.id]}, format="json"
        )
        self.assertEqual(len(restored.json()["crops"]), 2)

        for bad in ({}, {"farmer_name": ""}, {"farmer_name": None}, {"crop_ids": []}):
            with self.subTest(bad=bad):
                response = self.client.patch(url, bad, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        visit.refresh_from_db()
        self.assertEqual(visit.farmer_name, "Ramesh Patel")

    def test_edit_farmer_visit_changes_contact_village_and_land(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_edit_farmer_visit_changes_contact_village_and_land"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        visit = self.make_visit(trip)
        other = self.make_visit(trip, contact_number="9876500002")
        url = EDIT_VISIT_URL.format(public_id=visit.public_id)

        ok = self.client.patch(
            url,
            {"contact_number": "9876500003", "village": " New Village ", "land_area_bigha": "4.5"},
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        body = ok.json()
        self.assertEqual(body["contact_number"], "9876500003")
        self.assertEqual(body["village"], "New Village")
        self.assertEqual(body["land_area_bigha"], "4.5000")
        self.assertEqual(body["farmer_name"], "Ramesh Patel")

        same = self.client.patch(url, {"contact_number": "9876500003"}, format="json")
        self.assertEqual(same.status_code, status.HTTP_200_OK)

        for bad in (
            {"contact_number": other.contact_number},
            {"contact_number": "123"},
            {"village": " "},
            {"land_area_bigha": "-1"},
        ):
            with self.subTest(bad=bad):
                response = self.client.patch(url, bad, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_another_sales_persons_farmer_visit_is_not_found(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_another_sales_persons_farmer_visit_is_not_found"""
        theirs = self.make_trip(owner=self.other_sales_person, status=StatusIds.IN_PROGRESS)
        visit = self.make_visit(theirs)
        response = self.client.patch(
            EDIT_VISIT_URL.format(public_id=visit.public_id), {"farmer_name": "X"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        visit.refresh_from_db()
        self.assertEqual(visit.farmer_name, "Ramesh Patel")

    def test_utilities_return_every_crop_and_product_unpaginated(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_utilities_return_every_crop_and_product_unpaginated"""
        crops = self.client.get(CROPS_URL)
        self.assertEqual(crops.status_code, status.HTTP_200_OK)
        self.assertEqual(len(crops.json()), Crop.objects.count())
        self.assertEqual(
            crops.json()[0], {"id": self.bajari.id, "name": "Bajari", "is_deleted": False}
        )

        products = self.client.get(PRODUCTS_URL)
        self.assertEqual(products.status_code, status.HTTP_200_OK)
        self.assertEqual(len(products.json()), Product.objects.count())
        row = next(p for p in products.json() if p["public_id"] == self.castor_seed.public_id)
        self.assertEqual((row["crop_id"], row["crop"]), (self.castor.id, "Castor"))

    def test_a_frozen_product_stays_in_the_farmer_picker_flagged(self):
        """Farmers and field trips are the one place a frozen product stays visible.

        tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_a_frozen_product_stays_in_the_farmer_picker_flagged
        """
        Product.objects.filter(pk=self.castor_seed.pk).update(is_usable=False)

        rows = {row["public_id"]: row for row in self.client.get(PRODUCTS_URL).json()}
        self.assertFalse(rows[self.castor_seed.public_id]["is_usable"])

    def test_utilities_show_soft_deleted_rows_only_on_request(self):
        """tests/android/test_field_trips.py::AndroidFieldTripApiTest::test_utilities_show_soft_deleted_rows_only_on_request"""
        self.bajari.mark_deleted(self.superuser)
        self.castor_seed.mark_deleted(self.superuser)
        cases = {
            CROPS_URL: ("id", self.bajari.id),
            PRODUCTS_URL: ("public_id", self.castor_seed.public_id),
        }
        for url, (key, deleted_key) in cases.items():
            with self.subTest(url=url):
                hidden = self.client.get(url).json()
                self.assertNotIn(deleted_key, [row[key] for row in hidden])
                self.assertFalse(any(row["is_deleted"] for row in hidden))

                for query in ("show_deleted=true", "show_deleted"):
                    shown = {row[key]: row for row in self.client.get(f"{url}?{query}").json()}
                    self.assertTrue(shown[deleted_key]["is_deleted"])
                    self.assertEqual(len(shown), len(hidden) + 1)

                off = self.client.get(f"{url}?show_deleted=false").json()
                self.assertEqual(off, hidden)
                bad = self.client.get(f"{url}?show_deleted=maybe")
                self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
