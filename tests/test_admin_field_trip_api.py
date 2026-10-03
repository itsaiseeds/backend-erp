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
from unittest import mock

from django.utils.dateparse import parse_datetime
from rest_framework import status

from aggregator.models import FarmerVisit, FieldTrip, Notification
from aggregator.models.Status import StatusIds
from tests.common import WebApiTestCase
from tests.field_trip_fixtures import FieldTripFixtures

LIST_URL = "/api/sales-admin/field-trips/"
DETAIL_URL = "/api/sales-admin/field-trip/{public_id}"
VISITS_URL = "/api/sales-admin/field-trip-farmer-visits/{public_id}"
FARMERS_URL = "/api/sales-admin/farmers/"
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
        # TestCase never commits, so run the post-commit notification inline.
        patcher = mock.patch(
            "aggregator.NotificationOperations.fire_and_forget",
            side_effect=lambda func: func(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        push = mock.patch("aggregator.NotificationOperations.send_push", return_value=[])
        push.start()
        self.addCleanup(push.stop)

    def _ids(self, response) -> list[str]:
        return [row["public_id"] for row in response.json()["results"]]

    def _notification(self, trip: FieldTrip) -> Notification:
        """The planner's newest notification about ``trip``."""
        return Notification.objects.filter(
            recipient_id=trip.created_by_id,
            event_type__startswith="FIELD_TRIP_",
        ).latest("id")

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

    def test_approving_and_unapproving_notify_the_planner(self):
        """The sales person who planned the trip hears the admin's decision, by name.

        tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_approving_and_unapproving_notify_the_planner
        """
        trip = self.make_trip()

        self.assertEqual(
            self.client.post(APPROVE_URL.format(public_id=trip.public_id)).status_code,
            status.HTTP_200_OK,
        )
        approved = self._notification(trip)
        self.assertEqual(approved.event_type, "FIELD_TRIP_APPROVED")
        self.assertEqual(approved.title, "Field trip approved")
        self.assertEqual(approved.body, f"{trip.public_id} to Kamrej was approved by Meera Desai.")
        self.assertEqual(approved.data, {"field_trip_public_id": trip.public_id})
        self.assertIsNone(approved.order)
        self.assertIsNone(approved.read_at)

        # An admin decision another sales person planned is theirs, not mine.
        mine_before = set(
            Notification.objects.filter(recipient=self.sales_person).values_list("id", flat=True)
        )
        theirs = self.make_trip(owner=self.other_sales_person, village="Olpad")
        self.assertEqual(
            self.client.post(APPROVE_URL.format(public_id=theirs.public_id)).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(self._notification(theirs).recipient, self.other_sales_person)
        self.assertEqual(
            set(
                Notification.objects.filter(recipient=self.sales_person).values_list(
                    "id", flat=True
                )
            ),
            mine_before,
        )

        self.assertEqual(
            self.client.post(UNAPPROVE_URL.format(public_id=trip.public_id)).status_code,
            status.HTTP_200_OK,
        )
        withdrawn = self._notification(trip)
        self.assertEqual(withdrawn.event_type, "FIELD_TRIP_UNAPPROVED")
        self.assertEqual(withdrawn.title, "Field trip approval withdrawn")
        self.assertEqual(
            withdrawn.body,
            f"{trip.public_id} to Kamrej had its approval withdrawn by Meera Desai.",
        )

    def test_a_refused_decision_notifies_nobody(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_a_refused_decision_notifies_nobody"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        before = Notification.objects.count()
        for url in (APPROVE_URL, UNAPPROVE_URL):
            with self.subTest(verb=url):
                response = self.client.post(url.format(public_id=trip.public_id))
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Notification.objects.count(), before)

    # -- farmers (every trip) ---------------------------------------------------

    def test_the_farmer_list_folds_repeat_meetings_into_one_farmer(self):
        """One row per contact number: the latest visit, everything merged.

        tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_the_farmer_list_folds_repeat_meetings_into_one_farmer
        """
        first_trip = self.make_trip(status=StatusIds.IN_PROGRESS, village="Kamrej")
        first = self.make_visit(
            first_trip,
            contact_number="9876500001",
            crops=[self.castor],
            products=[self.castor_seed],
            land_area_bigha="2.5",
        )
        other_trip = self.make_trip(
            owner=self.other_sales_person,
            status=StatusIds.IN_PROGRESS,
            city=self.other_city,
            village="Olpad",
        )
        ops = self.make_visit(
            other_trip,
            contact_number="9876500001",
            crops=[self.bajari],
            land_area_bigha="3.5",
        )
        ops.farmer_name = "Ramesh Patel Jr"
        ops.save(update_fields=["farmer_name", "updated_at"])
        self.make_visit(other_trip, contact_number="9876500002", crops=[self.bajari])

        response = self.client.get(FARMERS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total_count"], 2)
        rows = {row["contact_number"]: row for row in response.json()["results"]}
        self.assertEqual(set(rows), {"9876500001", "9876500002"})

        farmer = rows["9876500001"]
        # The latest visit speaks for name, village, city and land...
        self.assertEqual(farmer["farmer_name"], "Ramesh Patel Jr")
        self.assertEqual(farmer["village"], "Olpad")
        self.assertEqual(farmer["city"], {"id": self.other_city.id, "name": self.other_city.name})
        self.assertEqual(farmer["land_area_bigha"], "3.5000")
        # ...while the crops and the meeting history are merged over both visits.
        self.assertEqual(
            farmer["crops"],
            [
                {"id": self.bajari.id, "name": "Bajari"},
                {"id": self.castor.id, "name": "Castor"},
            ],
        )
        self.assertTrue(farmer["uses_our_products"])
        self.assertEqual(
            farmer["products"],
            [{"public_id": self.castor_seed.public_id, "name": self.castor_seed.name}],
        )
        self.assertEqual(farmer["visit_count"], 2)
        self.assertEqual(
            [visit["public_id"] for visit in farmer["visits"]], [ops.public_id, first.public_id]
        )
        self.assertEqual(
            [visit["field_trip_public_id"] for visit in farmer["visits"]],
            [other_trip.public_id, first_trip.public_id],
        )
        self.assertEqual(parse_datetime(farmer["last_visited_at"]), ops.created_at)
        self.assertEqual(
            farmer["sales_people"],
            [
                {"id": self.sales_person.id, "name": "Sales One"},
                {"id": self.other_sales_person.id, "name": "Sales Two"},
            ],
        )
        self.assertFalse(rows["9876500002"]["uses_our_products"])

        # Fewest meetings first; the repeat farmer sorts last.
        sorted_rows = self.client.get(f"{FARMERS_URL}?sort=visit_count").json()["results"]
        self.assertEqual(
            [row["contact_number"] for row in sorted_rows], ["9876500002", "9876500001"]
        )

    def test_a_deleted_visit_leaves_the_farmer_list(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_a_deleted_visit_leaves_the_farmer_list"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        visit = self.make_visit(trip)
        FarmerVisit.all_objects.filter(id=visit.id).update(is_deleted=True)

        response = self.client.get(FARMERS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total_count"], 0)

    def test_the_farmer_list_filters_on_any_visit(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_the_farmer_list_filters_on_any_visit"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS, village="Kamrej")
        self.make_visit(
            trip,
            contact_number="9876500001",
            crops=[self.castor],
            products=[self.castor_seed],
            land_area_bigha="2.5",
        )
        other_trip = self.make_trip(
            owner=self.other_sales_person,
            status=StatusIds.IN_PROGRESS,
            city=self.other_city,
            village="Olpad",
        )
        second = self.make_visit(
            other_trip, contact_number="9876500002", crops=[self.bajari], land_area_bigha="4"
        )
        second.farmer_name = "Anil Desai"
        second.save(update_fields=["farmer_name", "updated_at"])

        cases = {
            # The castor crop was on the *older* visit, yet the farmer is kept.
            f"crop={self.castor.id}": ["9876500001"],
            f"product={self.castor_seed.public_id}": ["9876500001"],
            "uses_our_products=true": ["9876500001"],
            "uses_our_products=false": ["9876500002"],
            "village=olp": ["9876500002"],
            f"city_id={self.other_city.id}": ["9876500002"],
            f"created_by={self.sales_person.id}": ["9876500001"],
            "contact_number=76500001": ["9876500001"],
            "farmer_name=ramesh": ["9876500001"],
            "land_area_gte=4": ["9876500002"],
            f"crop={self.castor.id}&village=olp": [],
            "sort=land_area": ["9876500001", "9876500002"],
            "sort=-land_area": ["9876500002", "9876500001"],
            "sort=farmer_name": ["9876500002", "9876500001"],
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                response = self.client.get(f"{FARMERS_URL}?{query}")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    [row["contact_number"] for row in response.json()["results"]], expected
                )

        response = self.client.get(FARMERS_URL)
        filters = {entry["filter"]: entry for entry in response.json()["available_filters"]}
        self.assertEqual(
            {option["value"] for option in filters["created_by"]["options"]},
            {self.sales_person.id, self.other_sales_person.id},
        )
        self.assertEqual(
            {option["value"] for option in filters["crop"]["options"]},
            {self.castor.id, self.bajari.id},
        )
        self.assertEqual(
            {option["value"] for option in filters["city_id"]["options"]},
            {self.city.id, self.other_city.id},
        )

    def test_the_farmer_list_pages(self):
        """tests/test_admin_field_trip_api.py::SalesAdminFieldTripApiTest::test_the_farmer_list_pages"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        self.make_visit(trip, contact_number="9876500001")
        self.make_visit(trip, contact_number="9876500002")

        first = self.client.get(FARMERS_URL, {"page_size": 1})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(
            (
                first.json()["total_count"],
                first.json()["total_pages"],
                first.json()["next_page_number"],
            ),
            (2, 2, 2),
        )
        self.assertEqual(len(first.json()["results"]), 1)

        second = self.client.get(FARMERS_URL, {"page_size": 1, "page": 2})
        self.assertEqual(second.json()["previous_page_number"], 1)
        self.assertIsNone(second.json()["next_page_number"])
        self.assertEqual(
            {row["contact_number"] for row in first.json()["results"] + second.json()["results"]},
            {"9876500001", "9876500002"},
        )

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
