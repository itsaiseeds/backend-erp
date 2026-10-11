"""Rejected orders, LR -> DELIVERED, mark delivered and the challan order-type filter.

``POST create-rejected-order``, ``GET rejected-orders/``, ``DELETE
rejected-order/<public_id>``, ``GET party-rejected-lots/<party_id>``,
``POST upload-lr-number``, ``POST mark-order-delivered`` and
``POST mark-custom-order-delivered``, ``GET dispatch-challans/?order_type=``.

A rejected order sells kilograms of specific lab-rejected lots. No action here
may un-sync the stock ledger, so every test ends in ``check_ledger() == []``
(``DMLTestCase`` asserts it as a cleanup once any ledger row exists; the tests
that book no stock assert it explicitly).

Authentication and role gating are proven once in
``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations, StockLedgerOperations
from aggregator.ClientOperations import create_client_with_details, verify_client
from aggregator.CustomOrderOperations import (
    create_custom_order,
    create_waste_order,
    dispatch_custom_order,
    revert_dispatch,
)
from aggregator.InwardOperations import locked_raw_lot, status_row_for
from aggregator.LabTestingOperations import update_lab_test
from aggregator.models import (
    City,
    Country,
    CustomOrder,
    InwardRawMaterial,
    InwardRawMaterialStatus,
    Party,
    PartyType,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
    StatusIds,
)
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.common import WebApiTestCase, book_raw_material_for_every_product, lab_verdict

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
CREATE_URL = "/api/sales-admin/create-rejected-order"
LIST_URL = "/api/sales-admin/rejected-orders/"
DELETE_URL = "/api/sales-admin/rejected-order/{public_id}"
DETAIL_URL = "/api/sales-admin/custom-order/{public_id}"
PARTY_LOTS_URL = "/api/sales-admin/party-rejected-lots/{party_id}"
REVERT_URL = "/api/sales-admin/revert-custom-order-dispatch/{public_id}"
EDIT_WASTE_URL = "/api/sales-admin/edit-waste-order/{public_id}"
DISPATCH_WASTE_URL = "/api/sales-admin/dispatch-waste-order/{public_id}"
MARK_CUSTOM_URL = "/api/sales-admin/mark-custom-order-delivered/{public_id}"
MARK_ORDER_URL = "/api/sales-admin/mark-order-delivered/{public_id}"
LR_URL = "/api/sales-admin/upload-lr-number/{public_id}"
REVERT_ORDER_URL = "/api/sales-admin/revert-dispatch/{public_id}"
CHALLANS_URL = "/api/sales-admin/dispatch-challans/"
EXPORT_URL = "/api/sales-admin/export/rejected-orders"

W1 = Decimal("1.000")


class RejectedOrderApiTest(WebApiTestCase):
    """Booking, listing, deleting and guarding rejected lots.

    tests/test_rejected_orders.py::RejectedOrderApiTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)

        cls.admin = User.objects.create_user(
            phone_number="9000000801",
            name="Admin One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin, created_by=cls.superuser, can_update_stock_count=True)
        sales_person = User.objects.create_user(
            phone_number="9000000802",
            name="Sales One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(user=sales_person, city=cls.city, created_by=cls.superuser)

        cls.acme = create_client_with_details(
            company_name="Acme Seeds",
            company_phone="9876543210",
            gst_number="27AAPFU0939F1ZV",
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "line_2": "",
                    "pincode": "395007",
                    "city": cls.city,
                    "state": cls.state,
                    "country": cls.country,
                    "label": "Warehouse",
                    "is_primary": True,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": "Acme Transport"}],
            actor=sales_person,
        )
        verify_client(cls.acme, cls.admin)

        cls.cotton = cls._product("Rejected Cotton", Decimal("100.00"))
        cls.wheat = cls._product("Rejected Wheat", Decimal("80.00"))
        book_raw_material_for_every_product(actor=cls.superuser)
        cls.party = Party.objects.create(
            name="Rejecting Farm", city_id=1, party_type=PartyType.RAW_MATERIAL, created_by=cls.superuser
        )
        cls.other_party = Party.objects.create(
            name="Other Farm", city_id=1, party_type=PartyType.RAW_MATERIAL, created_by=cls.superuser
        )

    @classmethod
    def _product(cls, name, rate):
        product = Product.objects.create(
            name=name,
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=rate,
            created_by=cls.superuser,
        )
        ProductPackaging.objects.create(
            product=product,
            packet_weight=W1,
            packets=10,
            selling_price=rate * 10,
            created_by=cls.superuser,
        )
        return product

    def setUp(self):
        super().setUp()
        self.login_as(self.admin)

    # -- helpers --------------------------------------------------------------

    def _lot(self, kg="100", *, product=None, party=None, lot_no="SUP-1", verdict="Fail"):
        lot = InwardOperations.create_raw_lot(
            product=product or self.cotton,
            party=party or self.party,
            lot_no=lot_no,
            farmer_name="Farmer Joe",
            quantity_kg=Decimal(kg),
            lab_sampling_date=indian_now().date(),
            actor=self.admin,
        )
        if verdict:
            lab_verdict(lot.public_id, verdict, actor=self.admin, comment="bad germination")
            lot.refresh_from_db()
        return lot

    def _address_id(self):
        return self.acme.client_addresses.get(address__city=self.city).id

    def _line(self, lot, kg, price="10.00", **extra):
        return {
            "inward_raw_material_public_id": lot.public_id,
            "quantity_kg": str(kg),
            "negotiated_selling_price": price,
            **extra,
        }

    def _create(self, items, **overrides):
        body = {
            "client_public_id": self.acme.public_id,
            "client_address_id": self._address_id(),
            "from_city_id": self.city.id,
            "driver_name": "Ramesh Driver",
            "driver_number": "9876500009",
            "vehicle_number": "GJ05AB1234",
            "items": items,
            **overrides,
        }
        return self.client.post(CREATE_URL, body, format="json")

    def _book(self, *lines, **overrides):
        response = self._create(list(lines), **overrides)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return CustomOrder.objects.get(public_id=response.data["public_id"])

    def _assert_ledger(self):
        self.assertEqual(StockLedgerOperations.check_ledger(), [])

    # -- booking --------------------------------------------------------------

    def test_booking_dispatches_at_once_and_moves_no_ledger_figure(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_booking_dispatches_at_once_and_moves_no_ledger_figure"""
        lot = self._lot("100")
        raw_before = inv.raw_available_kg(self.cotton)

        order = self._book(self._line(lot, "40", "12.50"))

        self.assertTrue(order.public_id.startswith("RORD-"))
        self.assertTrue(order.made_from_rejected)
        self.assertFalse(order.made_from_waste)
        self.assertEqual(order.status.code, "DISPATCHED")
        self.assertEqual(order.unit_of_measure, "kg")
        self.assertIsNotNone(order.private_dispatch_details_id)
        self.assertEqual(order.items.get().inward_raw_material, lot)
        self.assertEqual(inv.raw_available_kg(self.cotton), raw_before)
        self.assertEqual(inv.rejected_lot_remaining_kg(lot), Decimal("60.000"))
        self._assert_ledger()

    def test_lot_numbers_default_to_the_lots_own_and_can_be_overridden(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_lot_numbers_default_to_the_lots_own_and_can_be_overridden"""
        first = self._lot("100", lot_no="SUP-A")
        second = self._lot("100", lot_no="SUP-B")

        order = self._book(
            self._line(first, "10"), self._line(second, "10", lot_number="PRINT-9")
        )

        lines = {line.lot_number: line for line in order.dispatch_entry.items.all()}
        self.assertEqual(set(lines), {"SUP-A", "PRINT-9"})
        self.assertEqual(lines["SUP-A"].quantity_kg, Decimal("10.000"))
        self._assert_ledger()

    def test_two_lots_of_one_product_share_an_order_and_a_challan(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_two_lots_of_one_product_share_an_order_and_a_challan"""
        first = self._lot("50", lot_no="SUP-A")
        second = self._lot("50", lot_no="SUP-B")

        order = self._book(self._line(first, "50"), self._line(second, "25"))

        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.dispatch_entry.items.count(), 2)
        detail = self.client.get(DETAIL_URL.format(public_id=order.public_id))
        self.assertEqual(detail.data["order_kind"], "rejected")
        self.assertEqual(
            {item["lot"]["lot_no"] for item in detail.data["items"]}, {"SUP-A", "SUP-B"}
        )

    def test_same_lot_numbers_for_one_product_are_refused(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_same_lot_numbers_for_one_product_are_refused"""
        first = self._lot("50", lot_no="SUP-A")
        second = self._lot("50", lot_no="SUP-B")

        response = self._create(
            [self._line(first, "5", lot_number="X"), self._line(second, "5", lot_number="X")]
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CustomOrder.objects.filter(made_from_rejected=True).exists())

    def test_booking_more_than_the_remaining_kg_is_refused(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_booking_more_than_the_remaining_kg_is_refused"""
        lot = self._lot("100")
        self._book(self._line(lot, "70"))

        response = self._create([self._line(lot, "40")])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CustomOrder.objects.filter(made_from_rejected=True).count(), 1)

    def test_only_live_rejected_dated_lots_are_bookable(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_only_live_rejected_dated_lots_are_bookable"""
        passed = self._lot("100", lot_no="PASS", verdict="Pass")
        in_lab = self._lot("100", lot_no="LAB", verdict=None)
        future = self._lot("100", lot_no="FUTURE")
        today = indian_now().date()
        InwardRawMaterial.objects.filter(pk=future.pk).update(
            effective_date=today + timedelta(days=1)
        )
        try:
            for lot in (passed, in_lab, future):
                response = self._create([self._line(lot, "1")])
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, lot.lot_no)
        finally:
            # Raw ORM moved a dated ledger figure; put it back for the ledger guard.
            InwardRawMaterial.objects.filter(pk=future.pk).update(effective_date=today)

    def test_a_lot_listed_twice_and_missing_driver_are_refused(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_a_lot_listed_twice_and_missing_driver_are_refused"""
        lot = self._lot("100")

        twice = self._create([self._line(lot, "1"), self._line(lot, "2")])
        no_driver = self._create([self._line(lot, "1")], driver_name="")

        self.assertEqual(twice.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(no_driver.status_code, status.HTTP_400_BAD_REQUEST)

    # -- listing / detail / export -------------------------------------------

    def test_lists_are_split_by_kind(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_lists_are_split_by_kind"""
        lot = self._lot("100")
        order = self._book(self._line(lot, "10"))

        rejected = self.client.get(LIST_URL)
        custom = self.client.get("/api/sales-admin/custom-orders/")
        waste = self.client.get("/api/sales-admin/waste-orders/")
        today = indian_now().date().isoformat()
        export = self.client.get(EXPORT_URL, {"start_date": today, "end_date": today})

        self.assertEqual([row["public_id"] for row in rejected.data["results"]], [order.public_id])
        self.assertEqual(custom.data["total_count"], 0)
        self.assertEqual(waste.data["total_count"], 0)
        self.assertEqual(export.status_code, status.HTTP_200_OK)
        self.assertEqual(rejected.data["results"][0]["made_from_waste"], False)
        self.assertEqual(rejected.data["results"][0]["made_from_rejected"], True)

    # -- delete ---------------------------------------------------------------

    def test_delete_frees_the_lot_the_same_day(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_delete_frees_the_lot_the_same_day"""
        lot = self._lot("100")
        order = self._book(self._line(lot, "100"))

        response = self.client.delete(DELETE_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomOrder.objects.filter(pk=order.pk).exists())
        self.assertEqual(inv.rejected_lot_remaining_kg(lot), Decimal("100.000"))
        self._book(self._line(lot, "100"))
        self._assert_ledger()

    def test_delete_is_refused_the_next_day_and_after_delivery(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_delete_is_refused_the_next_day_and_after_delivery"""
        lot = self._lot("100")
        old = self._book(self._line(lot, "10"))
        delivered = self._book(self._line(lot, "10"))
        self.client.post(MARK_CUSTOM_URL.format(public_id=delivered.public_id))
        yesterday = indian_now() - timedelta(days=1)
        old.dispatch_entry.__class__.objects.filter(pk=old.dispatch_entry.pk).update(
            dispatched_at=yesterday
        )
        old.private_dispatch_details.__class__.objects.filter(
            pk=old.private_dispatch_details_id
        ).update(dispatch_date=yesterday.date())

        stale = self.client.delete(DELETE_URL.format(public_id=old.public_id))
        gone = self.client.delete(DELETE_URL.format(public_id=delivered.public_id))

        self.assertEqual(stale.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(gone.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revert_edit_dispatch_and_plain_delete_are_refused(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_revert_edit_dispatch_and_plain_delete_are_refused"""
        lot = self._lot("100")
        order = self._book(self._line(lot, "10"))

        responses = [
            self.client.post(REVERT_URL.format(public_id=order.public_id)),
            self.client.patch(
                EDIT_WASTE_URL.format(public_id=order.public_id), {"special_comments": "x"}, format="json"
            ),
            self.client.post(
                DISPATCH_WASTE_URL.format(public_id=order.public_id),
                {
                    "from_city_id": self.city.id,
                    "driver_name": "A",
                    "driver_number": "9876500009",
                    "vehicle_number": "GJ05AB1234",
                },
                format="json",
            ),
            self.client.delete(DETAIL_URL.format(public_id=order.public_id)),
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        order.refresh_from_db()
        self.assertEqual(order.status.code, "DISPATCHED")

    def test_revert_dispatch_operation_refuses_a_rejected_order(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_revert_dispatch_operation_refuses_a_rejected_order"""
        lot = self._lot("100")
        order = self._book(self._line(lot, "10"))

        with self.assertRaises(ValidationError):
            revert_dispatch(order)

    # -- lot guards -----------------------------------------------------------

    def test_a_booked_lot_cannot_leave_rejected(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_a_booked_lot_cannot_leave_rejected"""
        lot = self._lot("100")
        self._book(self._line(lot, "10"))

        with self.assertRaises(ValidationError), transaction.atomic():
            update_lab_test(locked_raw_lot(InwardRawMaterial.objects.all(), lot.public_id), {"result": "Pass"}, self.admin)
        revert = self.client.patch(
            f"/api/sales-admin/inward-raw-material/{lot.public_id}",
            {"status": InwardRawMaterialStatus.LAB_TESTING.value},
            format="json",
        )
        delete = self.client.delete(f"/api/sales-admin/inward-raw-material/{lot.public_id}")

        self.assertEqual(revert.status_code, status.HTTP_400_BAD_REQUEST, revert.data)
        self.assertEqual(delete.status_code, status.HTTP_400_BAD_REQUEST, delete.data)
        lot.refresh_from_db()
        self.assertEqual(lot.status_id, StatusIds.RAW_MATERIAL_REJECTED.value)
        self._assert_ledger()

    def test_an_unbooked_lot_can_still_be_reverted(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_an_unbooked_lot_can_still_be_reverted"""
        lot = self._lot("100")
        with transaction.atomic():
            InwardOperations.update_raw_lot(
                locked_raw_lot(InwardRawMaterial.objects.all(), lot.public_id),
                {
                    "status": status_row_for(InwardRawMaterialStatus.LAB_TESTING),
                    "effective_date": None,
                },
                self.admin,
            )
        self._assert_ledger()

    # -- party lots -----------------------------------------------------------

    def test_party_rejected_lots_show_booked_and_remaining_kg(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_party_rejected_lots_show_booked_and_remaining_kg"""
        mine = self._lot("100", lot_no="MINE")
        self._lot("100", lot_no="THEIRS", party=self.other_party)
        self._lot("100", lot_no="PASSED", verdict="Pass")
        self._book(self._line(mine, "30"))

        response = self.client.get(PARTY_LOTS_URL.format(party_id=self.party.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data
        self.assertEqual([row["lot_no"] for row in rows], ["MINE"])
        row = rows[0]
        self.assertEqual(row["inward_raw_material_public_id"], mine.public_id)
        self.assertEqual(row["booked_kg"], "30.000")
        self.assertEqual(row["remaining_kg"], "70.000")
        self.assertEqual(row["party"], {"id": self.party.id, "name": "Rejecting Farm"})
        self.assertEqual(row["lab_test"]["result"], "Fail")
        self.assertEqual(row["lab_test"]["comment"], "bad germination")
        self.assertEqual(row["product"]["name"], "Rejected Cotton")

    def test_unknown_party_is_404(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_unknown_party_is_404"""
        response = self.client.get(PARTY_LOTS_URL.format(party_id=999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- challan filter -------------------------------------------------------

    def test_challan_list_filters_by_order_type(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_challan_list_filters_by_order_type"""
        lot = self._lot("100")
        rejected = self._book(self._line(lot, "10"))
        inv.record_raw_waste(product=self.wheat, quantity_kg=Decimal("20"), reason="r", actor=self.admin)
        waste = create_waste_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.get(address__city=self.city).address,
            actor=self.admin,
            items=[{"product": self.wheat, "quantity_kg": Decimal("5"), "negotiated_selling_price": Decimal("3")}],
        )
        inv.record_loose_stocks(counts={(self.cotton, W1): 10}, actor=self.admin)
        packet = create_custom_order(
            client=self.acme,
            delivery_address=waste.delivery_address,
            actor=self.admin,
            items=[{"product": self.cotton, "packet_weight": W1, "packets": 2}],
        )
        dispatch_custom_order(
            packet,
            actor=self.admin,
            from_city=self.city,
            driver_name="Ramesh",
            driver_number="9876500009",
            vehicle_number="GJ05AB1234",
            lot_numbers={(self.cotton.public_id, W1): "L-1"},
        )
        self.client.post(
            DISPATCH_WASTE_URL.format(public_id=waste.public_id),
            {
                "from_city_id": self.city.id,
                "driver_name": "A",
                "driver_number": "9876500009",
                "vehicle_number": "GJ05AB1234",
            },
            format="json",
        )

        now = indian_now()
        window = {
            "start_date_time": (now - timedelta(days=1)).isoformat(),
            "end_date_time": (now + timedelta(days=1)).isoformat(),
        }

        def challans(query=None):
            return self.client.get(CHALLANS_URL, {**window, **(query or {})})

        def order_ids(query):
            response = challans(query)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            return {row["order_public_id"] for row in response.data["results"]}

        self.assertEqual(order_ids({"order_type": "REJECTED_ORDER"}), {rejected.public_id})
        self.assertEqual(order_ids({"order_type": "WASTE_ORDER"}), {waste.public_id})
        self.assertEqual(order_ids({"order_type": "CUSTOM_ORDER"}), {packet.public_id})
        self.assertEqual(
            order_ids({"order_type": "WASTE_ORDER,REJECTED_ORDER"}),
            {waste.public_id, rejected.public_id},
        )
        self.assertEqual(order_ids({"order_type": "NORMAL_ORDER"}), set())
        self.assertEqual(challans({"order_type": "BOGUS"}).status_code, 400)
        challan = challans({"order_type": "REJECTED_ORDER"}).data["results"][0]
        self.assertEqual(challan["order_type"], "REJECTED_ORDER")
        filters = {entry["filter"]: entry for entry in challans().data["available_filters"]}
        self.assertIn("order_type", filters)
        self._assert_ledger()

    # -- mark delivered -------------------------------------------------------

    def test_mark_custom_order_delivered_accepts_rejected_orders(self):
        """tests/test_rejected_orders.py::RejectedOrderApiTest::test_mark_custom_order_delivered_accepts_rejected_orders"""
        lot = self._lot("100")
        order = self._book(self._line(lot, "10"))

        response = self.client.post(MARK_CUSTOM_URL.format(public_id=order.public_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "DELIVERED")
        self.assertEqual(inv.rejected_lot_remaining_kg(lot), Decimal("90.000"))
        self._assert_ledger()
