"""ORM-backed tests for ``aggregator.LabTestingOperations``.

A lab tester's verdict decides an inward raw lot: Pass -> In Use, Fail ->
Rejected, both stamping today. These tests drive the operations layer directly;
the endpoints that reach it are covered in ``tests/android/test_lab_tester.py``.
Every test also runs the stock-ledger guard (``DMLTestCase``), so a verdict that
moved stock without recording it fails here.
"""

from __future__ import annotations

from decimal import Decimal
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import transaction

from aggregator import InventoryOperations, InwardOperations
from aggregator.InwardOperations import locked_raw_lot, raw_status_of, status_row_for, today
from aggregator.LabTestingOperations import (
    lab_testing_payload,
    submit_lab_test,
    update_lab_test,
)
from aggregator.models import (
    InwardRawMaterial,
    InwardRawMaterialStatus,
    LabTesting,
    Notification,
    Party,
    Product,
    ProductPackaging,
)
from authentication.models import LabTester, User
from tests.common import DMLTestCase

SUPERUSER_PHONE = "9999999999"
LOT_QUERYSET = InwardRawMaterial.objects.select_related(
    "product", "party", "status", "created_by", "return_order__order", "lab_testing"
)

def make_tester(superuser: User, phone: str, name: str) -> User:
    """A verified user holding a live ``LabTester`` profile."""
    user = User.objects.create_user(
        phone_number=phone,
        name=name,
        is_verified=True,
        created_by=superuser,
        verified_by=superuser,
    )
    LabTester.objects.create(user=user, created_by=superuser)
    return user


# The inputs of a healthy test: 200 plants, 3 female, 1 OT -> impurity 2.00%, grow-out 98.00%.
INPUTS = {
    "number_of_plants": 200,
    "female_count": 3,
    "ot_count": 1,
    "result": "Pass",
    "comment": "healthy stand",
}


class LabTestingOperationsTest(DMLTestCase):
    """tests/test_lab_testing_operations.py::LabTestingOperationsTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.tester = make_tester(cls.superuser, "7100000001", "lab tester one")
        cls.product = Product.objects.get(name="SAI-33")
        cls.party = Party.objects.create(name="Lab Party", city_id=1, created_by=cls.superuser)

    # -- helpers --------------------------------------------------------------

    def _book(self, quantity_kg: str = "100") -> InwardRawMaterial:
        """A freshly booked lot, in Lab Testing."""
        return InwardOperations.create_raw_lot(
            product=self.product,
            party=self.party,
            lot_no="SUP-LAB-1",
            quantity_kg=Decimal(quantity_kg),
            lab_sampling_date=today(),
            actor=self.superuser,
        )

    def _lot(self, lot: InwardRawMaterial) -> InwardRawMaterial:
        """Reload ``lot`` the way the endpoints do (pool locked, joins loaded)."""
        return locked_raw_lot(LOT_QUERYSET, lot.public_id)

    def _inputs(self, **overrides) -> dict:
        return {**INPUTS, **overrides}

    def _submit(self, lot: InwardRawMaterial, **overrides) -> LabTesting:
        with transaction.atomic():
            return submit_lab_test(self._lot(lot), self._inputs(**overrides), self.tester)

    def _update(self, lot: InwardRawMaterial, **values) -> LabTesting:
        with transaction.atomic():
            return update_lab_test(self._lot(lot), values, self.tester)

    def _revert(self, lot: InwardRawMaterial) -> None:
        """What an admin's revert does (``UpdateInwardRawMaterialSerializer``)."""
        with transaction.atomic():
            InwardOperations.update_raw_lot(
                self._lot(lot),
                {
                    "status": status_row_for(InwardRawMaterialStatus.LAB_TESTING),
                    "effective_date": None,
                    "lab_sampling_date": today(),
                },
                self.superuser,
            )

    def _status(self, lot: InwardRawMaterial) -> InwardRawMaterialStatus:
        return raw_status_of(self._lot(lot))

    def _pack_a_bag(self) -> None:
        """Count one 10 kg bag of the product, so 10 kg of its raw lot is packed."""
        packaging = ProductPackaging.objects.create(
            product=self.product,
            packet_weight=Decimal("2.500"),
            packets=4,
            selling_price=Decimal("1000.00"),
            created_by=self.superuser,
        )
        InventoryOperations.record_stock_count(
            product_packaging=packaging, bags=1, actor=self.superuser
        )

    # -- computed figures ----------------------------------------------------------

    def test_impurity_and_grow_out_are_computed_from_the_counts(self):
        """(female + OT) / plants * 100, and 100 minus that, to two decimals.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_impurity_and_grow_out_are_computed_from_the_counts
        """
        test = self._submit(self._book())

        self.assertEqual(test.genetical_impurity, Decimal("2.00"))
        self.assertEqual(test.grow_out_test, Decimal("98.00"))

    def test_computed_figures_round_half_up_to_two_decimals(self):
        """1 female in 3 plants is 33.33% impurity and a 66.67% grow-out test.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_computed_figures_round_half_up_to_two_decimals
        """
        test = self._submit(
            self._book(), number_of_plants=3, female_count=1, ot_count=0, result="Fail"
        )

        self.assertEqual(test.genetical_impurity, Decimal("33.33"))
        self.assertEqual(test.grow_out_test, Decimal("66.67"))

    def test_the_verdict_is_independent_of_the_counts(self):
        """A spotless count can still be a Fail: the tester enters the result.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_the_verdict_is_independent_of_the_counts
        """
        lot = self._book()
        test = self._submit(lot, female_count=0, ot_count=0, result="Fail")

        self.assertEqual(test.grow_out_test, Decimal("100.00"))
        self.assertEqual(self._status(lot), InwardRawMaterialStatus.RAW_MATERIAL_REJECTED)

    # -- the verdict moves the lot ----------------------------------------------------

    def test_pass_makes_the_lot_in_use_and_counts_it_toward_raw_stock(self):
        """Pass -> In Use, effective date today, and the kilograms become packable.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_pass_makes_the_lot_in_use_and_counts_it_toward_raw_stock
        """
        lot = self._book("100")
        self.assertEqual(InventoryOperations.raw_available_kg(self.product), Decimal("0"))

        test = self._submit(lot, result="Pass")

        lot = self._lot(lot)
        self.assertEqual(raw_status_of(lot), InwardRawMaterialStatus.IN_USE)
        self.assertEqual(lot.effective_date, today())
        self.assertEqual(lot.lab_testing_id, test.pk)
        self.assertEqual(test.result, "Pass")
        self.assertEqual(test.tested_by_id, self.tester.id)
        self.assertIsNotNone(test.tested_at)
        self.assertEqual(InventoryOperations.raw_available_kg(self.product), Decimal("100"))

    def test_fail_rejects_the_lot_and_it_never_becomes_packable(self):
        """Fail -> Rejected, effective date today, and no usable kilograms.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_fail_rejects_the_lot_and_it_never_becomes_packable
        """
        lot = self._book("100")

        self._submit(lot, result="Fail")

        lot = self._lot(lot)
        self.assertEqual(raw_status_of(lot), InwardRawMaterialStatus.RAW_MATERIAL_REJECTED)
        self.assertEqual(lot.effective_date, today())
        self.assertEqual(InventoryOperations.raw_available_kg(self.product), Decimal("0"))
        line = next(
            row
            for row in InwardOperations.raw_incoming_stock()
            if row["public_id"] == self.product.public_id
        )
        self.assertEqual(line["rejected_kg"], Decimal("100"))

    def test_a_lot_that_is_not_in_lab_testing_cannot_be_tested(self):
        """Only a lot waiting in Lab Testing takes a first verdict.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_a_lot_that_is_not_in_lab_testing_cannot_be_tested
        """
        lot = self._book()
        self._submit(lot)

        with self.assertRaisesMessage(ValidationError, "Only a lot in Lab Testing"):
            self._submit(lot)
        self.assertEqual(LabTesting.objects.count(), 1)

    # -- validation: no negative / impossible figure ---------------------------------------

    def test_impossible_inputs_are_refused_and_move_nothing(self):
        """Female + OT above the plants, and zero plants are 400s.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_impossible_inputs_are_refused_and_move_nothing
        """
        lot = self._book()
        bad = {
            "more female + OT than plants": {"female_count": 150, "ot_count": 60},
            "zero plants": {"number_of_plants": 0},
        }
        for label, overrides in bad.items():
            with self.subTest(label), self.assertRaises(ValidationError):
                self._submit(lot, **overrides)

        self.assertEqual(self._status(lot), InwardRawMaterialStatus.LAB_TESTING)
        self.assertFalse(LabTesting.objects.exists())
        self.assertIsNone(self._lot(lot).effective_date)

    # -- sending a lot back, and re-testing it ----------------------------------------------

    def test_a_reverted_lot_keeps_its_inputs_and_is_retested_on_the_same_record(self):
        """Revert empties only the result; the next verdict updates the same LT row.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_a_reverted_lot_keeps_its_inputs_and_is_retested_on_the_same_record
        """
        lot = self._book()
        first = self._submit(lot, result="Pass", comment="first pass")

        self._revert(lot)

        reverted = self._lot(lot).lab_testing
        self.assertEqual(reverted.pk, first.pk)
        self.assertIsNone(reverted.result)
        self.assertEqual(reverted.number_of_plants, 200)
        self.assertEqual(reverted.comment, "first pass")
        self.assertEqual(self._status(lot), InwardRawMaterialStatus.LAB_TESTING)
        self.assertIsNone(self._lot(lot).effective_date)

        second = self._submit(lot, result="Fail", number_of_plants=100, comment="retest")

        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.public_id, first.public_id)
        self.assertEqual(LabTesting.objects.count(), 1)
        self.assertEqual(second.number_of_plants, 100)
        self.assertEqual(self._status(lot), InwardRawMaterialStatus.RAW_MATERIAL_REJECTED)

    def test_the_first_result_sent_on_a_reverted_lot_is_the_retest(self):
        """update_lab_test on a lot awaiting re-test, given a result, behaves as a submit.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_the_first_result_sent_on_a_reverted_lot_is_the_retest
        """
        lot = self._book()
        self._submit(lot, result="Fail")
        self._revert(lot)

        test = self._update(lot, result="Pass", comment="retested")

        self.assertEqual(test.result, "Pass")
        self.assertEqual(self._status(lot), InwardRawMaterialStatus.IN_USE)
        self.assertEqual(self._lot(lot).effective_date, today())

    def test_inputs_of_a_lot_awaiting_retest_can_be_corrected_without_a_verdict(self):
        """Editing the counts before re-testing neither moves the lot nor sets a result.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_inputs_of_a_lot_awaiting_retest_can_be_corrected_without_a_verdict
        """
        lot = self._book()
        self._submit(lot, result="Pass")
        self._revert(lot)

        test = self._update(lot, number_of_plants=400)

        self.assertEqual(test.number_of_plants, 400)
        self.assertIsNone(test.result)
        self.assertEqual(self._status(lot), InwardRawMaterialStatus.LAB_TESTING)

    # -- editing a verdict ----------------------------------------------------------------

    def test_editing_inputs_never_moves_the_lot(self):
        """Counts and comment are always editable, whatever the stock does.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_editing_inputs_never_moves_the_lot
        """
        lot = self._book()
        self._submit(lot, result="Pass")
        self._pack_a_bag()

        test = self._update(lot, female_count=10, comment="recounted")

        self.assertEqual(test.female_count, 10)
        self.assertEqual(test.comment, "recounted")
        self.assertEqual(test.result, "Pass")
        self.assertEqual(self._status(lot), InwardRawMaterialStatus.IN_USE)

    def test_pass_to_fail_is_refused_while_bags_are_packed_from_the_lot(self):
        """The lot's kilograms are packed, so failing it would make raw stock negative.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_pass_to_fail_is_refused_while_bags_are_packed_from_the_lot
        """
        lot = self._book("100")
        self._submit(lot, result="Pass")
        self._pack_a_bag()  # 10 kg of the 100 kg lot is now packed

        with self.assertRaisesMessage(ValidationError, "already packed"):
            self._update(lot, result="Fail")

        self.assertEqual(self._status(lot), InwardRawMaterialStatus.IN_USE)
        self.assertEqual(self._lot(lot).lab_testing.result, "Pass")
        self.assertGreaterEqual(InventoryOperations.raw_available_kg(self.product), 0)

    def test_pass_to_fail_is_allowed_when_nothing_is_packed_from_the_lot(self):
        """With no bags packed, a Pass can be corrected to a Fail.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_pass_to_fail_is_allowed_when_nothing_is_packed_from_the_lot
        """
        lot = self._book("100")
        self._submit(lot, result="Pass")

        test = self._update(lot, result="Fail")

        self.assertEqual(test.result, "Fail")
        self.assertEqual(self._status(lot), InwardRawMaterialStatus.RAW_MATERIAL_REJECTED)
        self.assertEqual(self._lot(lot).effective_date, today())
        self.assertEqual(InventoryOperations.raw_available_kg(self.product), Decimal("0"))

    def test_fail_to_pass_is_always_allowed(self):
        """Passing a rejected lot only adds kilograms, so nothing can go negative.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_fail_to_pass_is_always_allowed
        """
        lot = self._book("100")
        self._submit(lot, result="Fail")
        self._pack_a_bag_from_other_lot()

        test = self._update(lot, result="Pass")

        self.assertEqual(test.result, "Pass")
        self.assertEqual(self._status(lot), InwardRawMaterialStatus.IN_USE)

    def _pack_a_bag_from_other_lot(self) -> None:
        """Pack a bag backed by a different, already-passed lot of the same product."""
        other = self._book("50")
        self._submit(other, result="Pass")
        self._pack_a_bag()

    def test_a_tester_without_a_live_profile_is_not_a_lab_tester(self):
        """A soft-deleted LabTester profile no longer confers the role.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_a_tester_without_a_live_profile_is_not_a_lab_tester
        """
        user = make_tester(self.superuser, "7100000002", "to be removed")
        self.assertTrue(user.is_lab_tester)
        self.assertEqual(user.role, "lab_tester")

        user.lab_tester_profile.mark_deleted(self.superuser)

        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.is_lab_tester)
        self.assertEqual(user.role, "user")

    # -- payload ---------------------------------------------------------------------------

    def test_the_payload_carries_inputs_computed_figures_and_the_lot(self):
        """Everything the app shows for one test, in the shapes the other lot payloads use.

        tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_the_payload_carries_inputs_computed_figures_and_the_lot
        """
        lot = self._book("100")
        test = self._submit(lot, result="Pass")

        payload = lab_testing_payload(test, self._lot(lot))

        self.assertEqual(payload["public_id"], test.public_id)
        self.assertTrue(payload["public_id"].startswith("LT-"))
        self.assertEqual(payload["genetical_impurity"], "2.00")
        self.assertEqual(payload["grow_out_test"], "98.00")
        self.assertEqual(payload["result"], "Pass")
        self.assertEqual(payload["tested_by"], {"id": self.tester.id, "name": "lab tester one"})
        self.assertEqual(payload["inward_raw_material"]["public_id"], lot.public_id)
        self.assertEqual(payload["inward_raw_material"]["status"], "In Use")
        self.assertEqual(payload["inward_raw_material"]["quantity_kg"], "100.000")
        lot_payload = InwardOperations.inward_raw_material_payload(self._lot(lot))
        self.assertEqual(
            lot_payload["lab_testing"],
            {"public_id": test.public_id, "result": "Pass", "grow_out_test": "98.00"},
        )

    def test_an_untested_lot_has_no_lab_testing_block(self):
        """tests/test_lab_testing_operations.py::LabTestingOperationsTest::test_an_untested_lot_has_no_lab_testing_block"""
        lot = self._book()

        self.assertIsNone(InwardOperations.inward_raw_material_payload(self._lot(lot))["lab_testing"])


class LabTestNotificationTest(DMLTestCase):
    """Every live lab tester is told when a lot enters Lab Testing.

    tests/test_lab_testing_operations.py::LabTestNotificationTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.one = make_tester(cls.superuser, "7100000011", "tester one")
        cls.two = make_tester(cls.superuser, "7100000012", "tester two")
        cls.gone = make_tester(cls.superuser, "7100000013", "tester gone")
        cls.product = Product.objects.get(name="SAI-33")
        cls.party = Party.objects.create(name="Lab Party", city_id=1, created_by=cls.superuser)

    def setUp(self):
        super().setUp()
        # TestCase never commits, so run the post-commit notification inline and record the push.
        for target, kwargs in (
            ("fire_and_forget", {"side_effect": lambda func: func()}),
            ("send_push", {"return_value": []}),
        ):
            patcher = mock.patch(f"aggregator.NotificationOperations.{target}", **kwargs)
            started = patcher.start()
            self.addCleanup(patcher.stop)
            if target == "send_push":
                self.send_push = started
        self.gone.lab_tester_profile.mark_deleted(self.superuser)

    def _book(self) -> InwardRawMaterial:
        return InwardOperations.create_raw_lot(
            product=self.product,
            party=self.party,
            lot_no="SUP-N-1",
            quantity_kg=Decimal("40"),
            lab_sampling_date=today(),
            actor=self.superuser,
        )

    def _lab_notifications(self):
        return Notification.objects.filter(event_type="LAB_TEST_REQUESTED")

    def _live_testers(self) -> set[int]:
        """Every live lab tester's user id: ours plus the one ``dml.sql`` seeds."""
        return set(LabTester.objects.values_list("user_id", flat=True))

    def test_booking_a_lot_notifies_each_live_lab_tester_once(self):
        """One inbox row and one push per live tester; a removed tester gets nothing.

        tests/test_lab_testing_operations.py::LabTestNotificationTest::test_booking_a_lot_notifies_each_live_lab_tester_once
        """
        lot = self._book()

        rows = self._lab_notifications()
        live = self._live_testers()
        self.assertTrue({self.one.id, self.two.id} <= live)
        self.assertNotIn(self.gone.id, live)
        self.assertEqual({row.recipient_id for row in rows}, live)
        self.assertEqual(rows.count(), len(live))
        row = rows.first()
        self.assertEqual(row.title, "Lab test requested")
        self.assertIn(lot.public_id, row.body)
        self.assertIn("SAI-33", row.body)
        self.assertIn("40.000 kg", row.body)
        self.assertEqual(row.data, {"inward_raw_material_public_id": lot.public_id})
        self.assertEqual(self.send_push.call_count, len(live))
        _tokens, title, _body, data = self.send_push.call_args.args
        self.assertEqual(title, "Lab test requested")
        self.assertEqual(data["screen"], "lab_test_pending")
        self.assertEqual(data["type"], "LAB_TEST_REQUESTED")

    def test_sending_a_lot_back_notifies_the_lab_testers_again(self):
        """An admin's revert puts the lot back in the queue, so testers hear about it again.

        tests/test_lab_testing_operations.py::LabTestNotificationTest::test_sending_a_lot_back_notifies_the_lab_testers_again
        """
        lot = self._book()
        self._lab_notifications().delete()
        lot = locked_raw_lot(LOT_QUERYSET, lot.public_id)
        InwardOperations.update_raw_lot(
            lot,
            {"status": status_row_for(InwardRawMaterialStatus.IN_USE), "effective_date": today()},
            self.superuser,
        )
        self.assertEqual(self._lab_notifications().count(), 0)

        InwardOperations.update_raw_lot(
            locked_raw_lot(LOT_QUERYSET, lot.public_id),
            {
                "status": status_row_for(InwardRawMaterialStatus.LAB_TESTING),
                "effective_date": None,
            },
            self.superuser,
        )

        self.assertEqual(self._lab_notifications().count(), len(self._live_testers()))

    def test_a_verdict_does_not_notify_anyone(self):
        """Moving the lot out of Lab Testing is not a lab request.

        tests/test_lab_testing_operations.py::LabTestNotificationTest::test_a_verdict_does_not_notify_anyone
        """
        lot = self._book()
        self._lab_notifications().delete()

        with transaction.atomic():
            submit_lab_test(
                locked_raw_lot(LOT_QUERYSET, lot.public_id),
                {
                    "number_of_plants": 10,
                    "female_count": 0,
                    "ot_count": 0,
                    "result": "Pass",
                    "comment": "",
                },
                self.one,
            )

        self.assertEqual(self._lab_notifications().count(), 0)

    def test_a_failure_to_notify_never_fails_the_booking(self):
        """The notification is best-effort: nothing it does can undo the lot.

        tests/test_lab_testing_operations.py::LabTestNotificationTest::test_a_failure_to_notify_never_fails_the_booking
        """
        with mock.patch(
            "aggregator.NotificationOperations.deliver_event",
            side_effect=RuntimeError("FCM exploded"),
        ):
            # fire_and_forget is patched inline here, so mirror its swallow-and-log contract.
            with mock.patch(
                "aggregator.NotificationOperations.fire_and_forget",
                side_effect=lambda func: self._swallow(func),
            ):
                lot = self._book()

        self.assertTrue(InwardRawMaterial.objects.filter(pk=lot.pk).exists())

    @staticmethod
    def _swallow(func):
        try:
            func()
        except Exception:  # noqa: BLE001 -- the real fire_and_forget logs and swallows
            return None
