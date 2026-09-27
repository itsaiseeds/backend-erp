"""Sales-admin field-trip endpoints.

``field-trips/`` (list), ``field-trip/<public_id>`` (detail + delete),
``field-trip-farmer-visits/<public_id>``, ``edit-field-trip/<public_id>`` and
``approve-`` / ``unapprove-field-trip/<public_id>``. The status rules
themselves are proven in ``tests/test_field_trip_operations.py``; this module
asserts the endpoints' wiring -- filters, payloads and HTTP status mapping.
Authentication and role gating are proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta

from rest_framework import status

from aggregator.models import FieldTrip
from aggregator.models.Status import StatusIds
from tests.common import WebApiTestCase
from tests.field_trip_fixtures import FieldTripFixtures

LIST_URL = "/api/sales-admin/field-trips/"
DETAIL_URL = "/api/sales-admin/field-trip/{public_id}"
VISITS_URL = "/api/sales-admin/field-trip-farmer-visits/{public_id}"
EDIT_URL = "/api/sales-admin/edit-field-trip/{public_id}"
APPROVE_URL = "/api/sales-admin/approve-field-trip/{public_id}"
UNAPPROVE_URL = "/api/sales-admin/unapprove-field-trip/{public_id}"


class SalesAdminFieldTripApiTest(FieldTripFixtures, WebApiTestCase):
    """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.set_up_field_trip_fixtures()

    def setUp(self):
        super().setUp()
        self.login_as(self.admin_user)

    def _ids(self, response) -> list[str]:
        return [row["public_id"] for row in response.json()["results"]]

    def test_list_filters_across_every_sales_person(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_list_filters_across_every_sales_person"""
        mine = self.make_trip(starts_in_days=1)
        approved = self.make_trip(status=StatusIds.APPROVED, starts_in_days=3, village="Olpad")
        theirs = self.make_trip(
            owner=self.other_sales_person, city=self.other_city, starts_in_days=2
        )

        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Default: latest planned start first.
        self.assertEqual(
            self._ids(response), [approved.public_id, theirs.public_id, mine.public_id]
        )
        filters = {entry["filter"]: entry for entry in response.json()["available_filters"]}
        self.assertEqual(
            {option["value"] for option in filters["created_by"]["options"]},
            {self.sales_person.id, self.other_sales_person.id},
        )

        cases = {
            f"created_by={self.other_sales_person.id}": [theirs.public_id],
            "status=approved": [approved.public_id],
            f"city_id={self.other_city.id}": [theirs.public_id],
            "village=olp": [approved.public_id],
            "sort=expected_start_at": [mine.public_id, theirs.public_id, approved.public_id],
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self._ids(self.client.get(f"{LIST_URL}?{query}")), expected)

        start = (mine.expected_start_at + timedelta(hours=1)).isoformat()
        response = self.client.get(LIST_URL, {"expected_start_lte": start})
        self.assertEqual(self._ids(response), [mine.public_id])

    def test_detail_returns_the_whole_trip(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_detail_returns_the_whole_trip"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        self.make_visit(trip)

        response = self.client.get(DETAIL_URL.format(public_id=trip.public_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["status"], "IN_PROGRESS")
        self.assertEqual(body["city"], {"id": self.city.id, "name": self.city.name})
        self.assertEqual(body["sales_person"]["id"], self.sales_person.id)
        self.assertEqual(body["approved_by"]["id"], self.admin_user.id)
        self.assertIsNotNone(body["started_at"])
        self.assertIsNone(body["ended_at"])
        self.assertEqual(body["farmer_visit_count"], 1)

        missing = self.client.get(DETAIL_URL.format(public_id="FT-NOPE"))
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_farmer_visits_are_listed_and_filtered_per_trip(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_farmer_visits_are_listed_and_filtered_per_trip"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        grower = self.make_visit(
            trip, contact_number="9876500001", crops=[self.bajari], products=[self.bajari_seed]
        )
        non_user = self.make_visit(trip, contact_number="9876500002", land_area_bigha="0.75")
        other_trip = self.make_trip(owner=self.other_sales_person, status=StatusIds.IN_PROGRESS)
        self.make_visit(other_trip)
        url = VISITS_URL.format(public_id=trip.public_id)

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._ids(response), [non_user.public_id, grower.public_id])
        row = response.json()["results"][1]
        self.assertEqual(row["crops"], [{"id": self.bajari.id, "name": "Bajari"}])
        self.assertTrue(row["uses_our_products"])

        cases = {
            f"crop={self.bajari.id}": [grower.public_id],
            f"product={self.bajari_seed.public_id}": [grower.public_id],
            "uses_our_products=false": [non_user.public_id],
            "sort=land_area": [non_user.public_id, grower.public_id],
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self._ids(self.client.get(f"{url}?{query}")), expected)

        missing = self.client.get(VISITS_URL.format(public_id="FT-NOPE"))
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_edit_only_before_approval(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_edit_only_before_approval"""
        planned = self.make_trip()
        response = self.client.patch(
            EDIT_URL.format(public_id=planned.public_id),
            {"village": "  Bardoli ", "city_id": self.other_city.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["village"], "Bardoli")
        self.assertEqual(response.json()["city"]["id"], self.other_city.id)

        approved = self.make_trip(status=StatusIds.APPROVED)
        response = self.client.patch(
            EDIT_URL.format(public_id=approved.public_id), {"village": "X"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.patch(
            EDIT_URL.format(public_id=planned.public_id),
            {"expected_end_at": planned.expected_start_at.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_and_unapprove(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_approve_and_unapprove"""
        trip = self.make_trip()
        response = self.client.post(APPROVE_URL.format(public_id=trip.public_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "APPROVED")
        self.assertEqual(response.json()["approved_by"]["id"], self.admin_user.id)

        again = self.client.post(APPROVE_URL.format(public_id=trip.public_id))
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(UNAPPROVE_URL.format(public_id=trip.public_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "PLANNED")
        self.assertIsNone(response.json()["approved_by"])

        started = self.make_trip(status=StatusIds.IN_PROGRESS)
        refused = self.client.post(UNAPPROVE_URL.format(public_id=started.public_id))
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_only_before_the_trip_starts(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_delete_only_before_the_trip_starts"""
        approved = self.make_trip(status=StatusIds.APPROVED)
        response = self.client.delete(DETAIL_URL.format(public_id=approved.public_id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FieldTrip.objects.filter(id=approved.id).exists())

        started = self.make_trip(status=StatusIds.IN_PROGRESS)
        response = self.client.delete(DETAIL_URL.format(public_id=started.public_id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(FieldTrip.objects.filter(id=started.id).exists())
