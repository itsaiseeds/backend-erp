"""Field-trip lifecycle and farmer visits: ``aggregator.FieldTripOperations``.

The domain rules, proven once here: which status each verb accepts, the
one-trip-at-a-time rule, the delete guard, the approval an owner's edit
withdraws, and what a farmer visit records. The endpoint modules
(``tests/test_admin_field_trip_api.py``, ``tests/android/test_field_trips.py``)
only assert their own wiring on top of this.
"""

from __future__ import annotations

import itertools

from django.core.exceptions import PermissionDenied, ValidationError

from aggregator import FieldTripOperations as ops
from aggregator.models import FieldTrip
from aggregator.models.Status import StatusIds
from tests.common import DMLTestCase
from tests.field_trip_fixtures import FieldTripFixtures


class FieldTripLifecycleTest(FieldTripFixtures, DMLTestCase):
    """tests/test_field_trip_operations.py::FieldTripLifecycleTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.set_up_field_trip_fixtures()

    def test_full_lifecycle_records_who_and_when(self):
        """tests/test_field_trip_operations.py::FieldTripLifecycleTest::test_full_lifecycle_records_who_and_when"""
        trip = self.make_trip()
        self.assertEqual(trip.status_code, "PLANNED")
        self.assertEqual(trip.public_id[:3], "FT-")

        ops.approve_field_trip(trip, self.admin_user)
        self.assertEqual((trip.status_code, trip.approved_by), ("APPROVED", self.admin_user))
        self.assertIsNotNone(trip.approved_at)

        ops.start_field_trip(trip)
        self.assertEqual(trip.status_code, "IN_PROGRESS")
        self.assertIsNotNone(trip.started_at)

        ops.end_field_trip(trip)
        trip.refresh_from_db()
        self.assertEqual(trip.status_code, "COMPLETED")
        self.assertGreaterEqual(trip.ended_at, trip.started_at)
        self.assertEqual(trip.approved_by, self.admin_user)

    def test_each_verb_refuses_every_other_status(self):
        """tests/test_field_trip_operations.py::FieldTripLifecycleTest::test_each_verb_refuses_every_other_status"""
        verbs = {
            "approve": (lambda trip: ops.approve_field_trip(trip, self.admin_user), {"PLANNED"}),
            "unapprove": (ops.unapprove_field_trip, {"APPROVED"}),
            "start": (ops.start_field_trip, {"APPROVED"}),
            "end": (ops.end_field_trip, {"IN_PROGRESS"}),
            "admin edit": (
                lambda trip: ops.edit_field_trip_as_admin(trip, village="X"),
                {"PLANNED"},
            ),
            "owner edit": (
                lambda trip: ops.edit_field_trip_as_owner(trip, village="X"),
                {"PLANNED", "APPROVED"},
            ),
        }
        phones = (f"91{n:08d}" for n in itertools.count())
        for name, (verb, allowed) in verbs.items():
            for status in StatusIds.field_trip_statuses():
                if status.name in allowed:
                    continue
                with self.subTest(verb=name, status=status.name):
                    # A fresh owner per trip, so the one-in-progress rule never interferes.
                    owner = self._sales_person(next(phones), "Tmp")
                    trip = self.make_trip(owner=owner, status=status)
                    with self.assertRaises(ValidationError):
                        verb(trip)

    def test_only_a_sales_admin_may_approve(self):
        """tests/test_field_trip_operations.py::FieldTripLifecycleTest::test_only_a_sales_admin_may_approve"""
        trip = self.make_trip()
        with self.assertRaises(PermissionDenied):
            ops.approve_field_trip(trip, self.sales_person)

    def test_unapprove_clears_the_approval(self):
        """tests/test_field_trip_operations.py::FieldTripLifecycleTest::test_unapprove_clears_the_approval"""
        trip = self.make_trip(status=StatusIds.APPROVED)
        ops.unapprove_field_trip(trip)
        trip.refresh_from_db()
        self.assertEqual(trip.status_code, "PLANNED")
        self.assertIsNone(trip.approved_by)
        self.assertIsNone(trip.approved_at)

    def test_a_sales_person_runs_one_trip_at_a_time(self):
        """tests/test_field_trip_operations.py::FieldTripLifecycleTest::test_a_sales_person_runs_one_trip_at_a_time"""
        running = self.make_trip(status=StatusIds.IN_PROGRESS)
        waiting = self.make_trip(status=StatusIds.APPROVED)
        with self.assertRaisesMessage(ValidationError, running.public_id):
            ops.start_field_trip(waiting)

        # Another sales person is unaffected, and ending the first frees the slot.
        self.make_trip(owner=self.other_sales_person, status=StatusIds.IN_PROGRESS)
        ops.end_field_trip(running)
        ops.start_field_trip(waiting)
        self.assertEqual(waiting.status_code, "IN_PROGRESS")

    def test_owner_edit_of_an_approved_trip_withdraws_the_approval(self):
        """tests/test_field_trip_operations.py::FieldTripLifecycleTest::test_owner_edit_of_an_approved_trip_withdraws_the_approval"""
        trip = self.make_trip(status=StatusIds.APPROVED)
        ops.edit_field_trip_as_owner(trip, village="Bardoli", city=self.other_city)
        trip.refresh_from_db()
        self.assertEqual((trip.status_code, trip.village), ("PLANNED", "Bardoli"))
        self.assertEqual(trip.city, self.other_city)
        self.assertIsNone(trip.approved_by)

    def test_expected_end_must_follow_the_start(self):
        """tests/test_field_trip_operations.py::FieldTripLifecycleTest::test_expected_end_must_follow_the_start"""
        trip = self.make_trip()
        with self.assertRaises(ValidationError):
            ops.edit_field_trip_as_owner(trip, expected_end_at=trip.expected_start_at)

    def test_only_a_sales_person_may_plan_a_trip(self):
        """tests/test_field_trip_operations.py::FieldTripLifecycleTest::test_only_a_sales_person_may_plan_a_trip"""
        with self.assertRaises(ValidationError):
            self.make_trip(owner=self.admin_user)


class FieldTripDeleteTest(FieldTripFixtures, DMLTestCase):
    """tests/test_field_trip_operations.py::FieldTripDeleteTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.set_up_field_trip_fixtures()

    def test_a_trip_that_has_not_started_can_be_deleted(self):
        """tests/test_field_trip_operations.py::FieldTripDeleteTest::test_a_trip_that_has_not_started_can_be_deleted"""
        for status in (StatusIds.PLANNED, StatusIds.APPROVED):
            with self.subTest(status=status.name):
                trip = self.make_trip(status=status)
                ops.delete_field_trip(trip, self.admin_user)
                self.assertFalse(FieldTrip.objects.filter(id=trip.id).exists())
                self.assertEqual(FieldTrip.all_objects.get(id=trip.id).deleted_by, self.admin_user)

    def test_a_started_trip_cannot_be_deleted_by_any_path(self):
        """tests/test_field_trip_operations.py::FieldTripDeleteTest::test_a_started_trip_cannot_be_deleted_by_any_path"""
        for status in (StatusIds.IN_PROGRESS, StatusIds.COMPLETED):
            trip = self.make_trip(status=status, owner=self._sales_person(f"92000000{status}", "T"))
            deletes = {
                "mark_deleted": lambda trip=trip: trip.mark_deleted(self.admin_user),
                # The Django admin path: a superuser holds the delete permission.
                "delete": lambda trip=trip: trip.delete(deleted_by=self.superuser),
            }
            for name, delete in deletes.items():
                with self.subTest(status=status.name, path=name):
                    with self.assertRaises(ValidationError):
                        delete()
                    self.assertTrue(FieldTrip.objects.filter(id=trip.id).exists())


class FarmerVisitTest(FieldTripFixtures, DMLTestCase):
    """tests/test_field_trip_operations.py::FarmerVisitTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.set_up_field_trip_fixtures()

    def test_a_visit_records_crops_products_and_defaults_the_village(self):
        """tests/test_field_trip_operations.py::FarmerVisitTest::test_a_visit_records_crops_products_and_defaults_the_village"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        visit = self.make_visit(
            trip, crops=[self.castor, self.bajari, self.castor], products=[self.castor_seed]
        )
        payload = ops.farmer_visit_payload(ops.farmer_visit_queryset().get(id=visit.id))

        self.assertEqual(payload["village"], "Kamrej")
        self.assertEqual({crop["name"] for crop in payload["crops"]}, {"Castor", "Bajari"})
        self.assertTrue(payload["uses_our_products"])
        self.assertEqual(
            payload["products"],
            [{"public_id": self.castor_seed.public_id, "name": self.castor_seed.name}],
        )

    def test_no_products_means_the_farmer_does_not_use_ours(self):
        """tests/test_field_trip_operations.py::FarmerVisitTest::test_no_products_means_the_farmer_does_not_use_ours"""
        visit = self.make_visit(self.make_trip(status=StatusIds.IN_PROGRESS))
        self.assertFalse(visit.uses_our_products)

    def test_visits_are_recorded_only_while_the_trip_is_in_progress(self):
        """tests/test_field_trip_operations.py::FarmerVisitTest::test_visits_are_recorded_only_while_the_trip_is_in_progress"""
        for status in (StatusIds.PLANNED, StatusIds.APPROVED, StatusIds.COMPLETED):
            with self.subTest(status=status.name):
                trip = self.make_trip(status=status)
                with self.assertRaises(ValidationError):
                    self.make_visit(trip)

    def test_invalid_visits_are_refused(self):
        """tests/test_field_trip_operations.py::FarmerVisitTest::test_invalid_visits_are_refused"""
        trip = self.make_trip(status=StatusIds.IN_PROGRESS)
        self.make_visit(trip, contact_number="9876500001")
        cases = {
            "duplicate contact on the trip": {"contact_number": "9876500001"},
            "bad contact number": {"contact_number": "98765"},
            "negative land": {"contact_number": "9876500002", "land_area_bigha": "-1"},
        }
        for name, kwargs in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ValidationError):
                    self.make_visit(trip, **kwargs)
        with self.assertRaises(ValidationError):
            ops.create_farmer_visit(
                trip,
                actor=self.sales_person,
                farmer_name="No Crops",
                contact_number="9876500003",
                land_area_bigha=1,
                crops=[],
            )
