"""``DispatchEntry.challan_number`` -- the dated serial, and how it survives.

The format itself (``YYYYMMDD-XXXX`` on the challan payload, the first dispatch
of a day being ``-0001``) is proven over the API in
``tests/test_dispatch_challans_api.py``. What lives here is everything the API
cannot reach: moving a dispatch to another day, a soft-deleted entry keeping its
number reserved, running out of numbers, and the IST day boundary. Those are
properties of ``DispatchEntry.save`` / ``next_challan_number``, so they are
tested against the model, not through a view.

Run: bash scripts/run.sh test tests/test_challan_number.py
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError

from aggregator.ClientOperations import add_client_address, create_client
from aggregator.DispatchOperations import sync_dispatch_entry
from aggregator.models import (
    Address,
    City,
    Country,
    DispatchEntry,
    Pincode,
    Stage,
    StageIds,
    State,
)
from aggregator.models.DispatchEntry import (
    CHALLAN_NUMBER_MAX_SEQUENCE,
    challan_day_prefix,
    next_challan_number,
)
from aggregator.OrderOperations import attach_dispatch_details, create_order
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import Admin, SalesPerson, User
from common.models import indian_now
from tests.common import DMLTestCase, book_raw_material_for_every_product


class ChallanNumberTest(DMLTestCase):
    """tests/test_challan_number.py::ChallanNumberTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.sp_user = User.objects.create_user(
            "9000000801", "Challan Sales", created_by=cls.su, verified_by=cls.su,
            is_verified=True,
        )
        cls.adm_user = User.objects.create_user(
            "9000000802", "Challan Admin", created_by=cls.su, verified_by=cls.su,
            is_verified=True,
        )
        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.su}
        )
        cls.state = State.objects.create(
            name="Maharashtra", country=cls.country, created_by=cls.su
        )
        cls.city = City.objects.create(name="Pune", state=cls.state, created_by=cls.su)
        cls.city2 = City.objects.create(name="Mumbai", state=cls.state, created_by=cls.su)
        cls.pincode = Pincode.objects.create(
            code="411001", city=cls.city, created_by=cls.su
        )
        SalesPerson.objects.create(user=cls.sp_user, city=cls.city, created_by=cls.su)
        Admin.objects.create(
            user=cls.adm_user, created_by=cls.su, can_update_stock_count=True
        )
        cls.addr = Address.objects.create(
            address_line_1="1 Main St", pincode=cls.pincode, city=cls.city,
            state=cls.state, country=cls.country, created_by=cls.su,
        )
        cls.client_obj = create_client(
            company_name="Challan Co", gst_number="27AAPFU0939F1ZV", actor=cls.sp_user
        )
        add_client_address(cls.client_obj, cls.addr, cls.sp_user, is_primary=True)
        cls.product = create_product(
            name="Challan Maize", crop="Maize", stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("150.00"), actor=cls.sp_user,
        )
        cls.pack = add_packaging(
            cls.product, packet_weight=Decimal("25.000"), packets=4, actor=cls.sp_user
        )
        book_raw_material_for_every_product(actor=cls.su)

    # -- helpers --------------------------------------------------------------

    def _dispatch(self, *, on=None):
        """Book an order and write its challan, dated ``on`` (default: now).

        Mirrors what ``dispatch_order`` does up to the status flip, which these
        tests do not need -- the number is assigned by ``DispatchEntry.save``.
        A date rather than a datetime is deliberately turned into **IST
        midnight**, the timestamp most likely to expose a UTC-vs-IST slip.
        """
        dispatched_at = on if on is not None else indian_now()
        order = create_order(
            client=self.client_obj,
            delivery_address=self.addr,
            actor=self.sp_user,
            items=[{"product_packaging": self.pack, "quantity": 1}],
        )
        attach_dispatch_details(
            order, dispatched_by=self.adm_user, dispatch_date=dispatched_at.date(),
            from_city=self.city, to_city=self.city2,
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
        )
        return sync_dispatch_entry(
            order, actor=self.adm_user, dispatched_at=dispatched_at,
            from_city=self.city, to_city=self.city2,
            driver_name="Ramesh Driver", driver_number="9876500009",
            vehicle_number="GJ05AB1234",
            lot_numbers={self.pack.public_id: "LOT-1"},
        )

    @staticmethod
    def _ist_midnight(day):
        return datetime.datetime.combine(
            day, datetime.time(), tzinfo=indian_now().tzinfo
        )

    def _move_to(self, entry, day):
        """Re-stamp ``entry``'s dispatch to IST midnight on ``day`` and save."""
        entry.dispatched_at = self._ist_midnight(day)
        entry.save()
        entry.refresh_from_db()
        return entry

    # -- the sequence ---------------------------------------------------------

    def test_the_first_dispatch_of_a_day_is_0001_and_the_next_0002(self):
        """tests/test_challan_number.py::ChallanNumberTest::test_the_first_dispatch_of_a_day_is_0001_and_the_next_0002"""
        prefix = challan_day_prefix(indian_now().date())

        first = self._dispatch()
        second = self._dispatch()

        self.assertEqual(first.challan_number, f"{prefix}0001")
        self.assertEqual(second.challan_number, f"{prefix}0002")

    def test_each_day_restarts_its_own_cycle(self):
        """tests/test_challan_number.py::ChallanNumberTest::test_each_day_restarts_its_own_cycle"""
        today = indian_now().date()
        yesterday = today - datetime.timedelta(days=1)

        self.assertEqual(
            self._dispatch(on=self._ist_midnight(yesterday)).challan_number,
            f"{challan_day_prefix(yesterday)}0001",
        )
        self.assertEqual(
            self._dispatch().challan_number, f"{challan_day_prefix(today)}0001"
        )

    def test_a_dispatch_stamped_at_ist_midnight_belongs_to_that_ist_day(self):
        """The column is timestamptz: a naive .date() would read yesterday.

        tests/test_challan_number.py::ChallanNumberTest::test_a_dispatch_stamped_at_ist_midnight_belongs_to_that_ist_day
        """
        day = indian_now().date() - datetime.timedelta(days=3)

        entry = self._dispatch(on=self._ist_midnight(day))

        self.assertEqual(entry.challan_number, f"{challan_day_prefix(day)}0001")
        # The stored UTC timestamp is on the previous calendar day (18:30 UTC),
        # which is exactly the slip this asserts against.
        self.assertEqual(entry.dispatch_date, day)

    # -- staying consistent ---------------------------------------------------

    def test_moving_a_dispatch_to_another_day_renumbers_it_for_that_day(self):
        """tests/test_challan_number.py::ChallanNumberTest::test_moving_a_dispatch_to_another_day_renumbers_it_for_that_day"""
        yesterday = indian_now().date() - datetime.timedelta(days=1)
        entry = self._dispatch()

        self._move_to(entry, yesterday)

        self.assertEqual(
            entry.challan_number, f"{challan_day_prefix(yesterday)}0001"
        )

    def test_moving_a_dispatch_within_its_own_day_keeps_its_number(self):
        """The number is quoted to the client; a later hour is not a new challan.

        tests/test_challan_number.py::ChallanNumberTest::test_moving_a_dispatch_within_its_own_day_keeps_its_number
        """
        entry = self._dispatch()
        original = entry.challan_number

        entry.dispatched_at = indian_now() + datetime.timedelta(seconds=1)
        entry.save()
        entry.refresh_from_db()

        self.assertEqual(entry.challan_number, original)

    def test_a_number_vacated_by_a_move_is_never_handed_out_again(self):
        """The case a count-based sequence would collide on.

        Three dispatches today take 0001-0003. The middle one moves to
        yesterday, so today holds two entries -- but the next dispatch must be
        0004, not 0003, which the live third entry still holds.

        tests/test_challan_number.py::ChallanNumberTest::test_a_number_vacated_by_a_move_is_never_handed_out_again
        """
        today = indian_now().date()
        prefix = challan_day_prefix(today)
        first, second, third = self._dispatch(), self._dispatch(), self._dispatch()
        self.assertEqual(third.challan_number, f"{prefix}0003")

        self._move_to(second, today - datetime.timedelta(days=1))

        fourth = self._dispatch()
        self.assertEqual(fourth.challan_number, f"{prefix}0004")
        # Gaps are the accepted cost: 0002 is simply not on this day any more.
        self.assertEqual(
            sorted(
                DispatchEntry.all_objects.filter(
                    challan_number__startswith=prefix
                ).values_list("challan_number", flat=True)
            ),
            [f"{prefix}0001", f"{prefix}0003", f"{prefix}0004"],
        )
        self.assertEqual(first.challan_number, f"{prefix}0001")

    def test_a_soft_deleted_entry_keeps_its_number_reserved(self):
        """tests/test_challan_number.py::ChallanNumberTest::test_a_soft_deleted_entry_keeps_its_number_reserved"""
        prefix = challan_day_prefix(indian_now().date())
        entry = self._dispatch()
        self.assertEqual(entry.challan_number, f"{prefix}0001")

        entry.mark_deleted(self.adm_user)

        self.assertEqual(self._dispatch().challan_number, f"{prefix}0002")

    def test_a_soft_delete_does_not_disturb_the_number(self):
        """The delete saves four columns; the number is not one of them.

        tests/test_challan_number.py::ChallanNumberTest::test_a_soft_delete_does_not_disturb_the_number
        """
        entry = self._dispatch()
        original = entry.challan_number

        entry.mark_deleted(self.adm_user)
        entry.refresh_from_db()

        self.assertTrue(entry.is_deleted)
        self.assertEqual(entry.challan_number, original)

    # -- the edges ------------------------------------------------------------

    def test_running_out_of_numbers_for_a_day_is_refused(self):
        """Four digits by contract: a 10000th dispatch is an error, not -10000.

        tests/test_challan_number.py::ChallanNumberTest::test_running_out_of_numbers_for_a_day_is_refused
        """
        today = indian_now().date()
        prefix = challan_day_prefix(today)
        entry = self._dispatch()
        DispatchEntry.all_objects.filter(pk=entry.pk).update(
            challan_number=f"{prefix}{CHALLAN_NUMBER_MAX_SEQUENCE}"
        )

        with self.assertRaises(ValidationError):
            next_challan_number(today)
