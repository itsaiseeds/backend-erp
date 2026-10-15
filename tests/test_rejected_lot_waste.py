"""Converting a lab-rejected lot to waste (and back).

``POST inward-raw-material/<IR-id>/convert-to-waste`` writes the whole lot off as a
linked ``RawMaterialWaste`` row; ``DELETE raw-material-waste/<WS-id>`` reverses it.
RAW ``rejected`` falls and ``wasted`` rises by the lot's kg, usable stock does not
move, and the ledger stays in sync after every step.

Authentication and role gating are proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator import InventoryOperations as inv
from aggregator import InwardOperations, StockLedgerOperations
from aggregator.ClientOperations import create_client_with_details, verify_client
from aggregator.CustomOrderOperations import create_waste_order
from aggregator.LabTestingOperations import update_lab_test
from aggregator.models import (
    City,
    Country,
    InwardRawMaterial,
    Party,
    PartyType,
    Product,
    ProductPackaging,
    RawMaterialWaste,
    Stage,
    StageIds,
    State,
    StockEvent,
    StockEventLine,
    StockEventType,
    StockPoolKind,
)
from aggregator.StockLedgerReport import product_ledger_rows
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.common import WebApiTestCase, book_raw_material_for_every_product, lab_verdict

User = get_user_model()

CONVERT_URL = "/api/sales-admin/inward-raw-material/{public_id}/convert-to-waste"
GODOWN_CONVERT_URL = "/android/api/v1/godown/inward-raw-material/{public_id}/convert-to-waste"
GODOWN_WASTE_URL = "/android/api/v1/godown/raw-material-waste/{public_id}"
LOT_URL = "/api/sales-admin/inward-raw-material/{public_id}"
WASTE_URL = "/api/sales-admin/raw-material-waste/{public_id}"
LOTS_URL = "/api/sales-admin/inward-raw-materials"
STOCK_URL = "/api/sales-admin/raw-material-stock"
CREATE_REJECTED_URL = "/api/sales-admin/create-rejected-order"
PARTY_LOTS_URL = "/api/sales-admin/party-rejected-lots/{party_id}"

W1 = Decimal("1.000")


class RejectedLotWasteTest(WebApiTestCase):
    """tests/test_rejected_lot_waste.py::RejectedLotWasteTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.admin = User.objects.create_user(
            phone_number="9000000901",
            name="Admin One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin, created_by=cls.superuser, can_update_stock_count=True)
        cls.sales_person = User.objects.create_user(
            phone_number="9000000902",
            name="Sales One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(user=cls.sales_person, city=cls.city, created_by=cls.superuser)
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
            actor=cls.sales_person,
        )
        verify_client(cls.acme, cls.admin)
        cls.cotton = Product.objects.create(
            name="Waste Cotton",
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )
        ProductPackaging.objects.create(
            product=cls.cotton,
            packet_weight=W1,
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=cls.superuser,
        )
        book_raw_material_for_every_product(actor=cls.superuser)
        cls.party = Party.objects.create(
            name="Rejecting Farm",
            city_id=1,
            party_type=PartyType.RAW_MATERIAL,
            created_by=cls.superuser,
        )

    def setUp(self):
        super().setUp()
        self.login_as(self.admin)

    # -- helpers --------------------------------------------------------------

    def _lot(self, kg="100", *, lot_no="SUP-1", verdict="Fail"):
        lot = InwardOperations.create_raw_lot(
            product=self.cotton,
            party=self.party,
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

    def _convert(self, lot, **body):
        return self.client.post(CONVERT_URL.format(public_id=lot.public_id), body, format="json")

    def _convert_ok(self, lot, **body):
        response = self._convert(lot, **body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return RawMaterialWaste.objects.get(public_id=response.data["public_id"])

    def _restore(self, waste):
        return self.client.delete(WASTE_URL.format(public_id=waste.public_id))

    def _raw_deltas(self, event_type):
        event = StockEvent.objects.filter(event_type=event_type, product=self.cotton).latest("id")
        line = StockEventLine.objects.get(event=event, pool_kind=StockPoolKind.RAW)
        return line.d_rejected, line.d_wasted, line.d_incoming or Decimal("0")

    def _assert_ledger(self):
        self.assertEqual(StockLedgerOperations.check_ledger(), [])

    def _stock_line(self):
        response = self.client.get(STOCK_URL)
        return next(
            line for line in response.data["lines"] if line["product"] == self.cotton.public_id
        )

    # -- convert and reverse ----------------------------------------------------

    def test_convert_then_restore_moves_rejected_to_wasted_and_nothing_else(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_convert_then_restore_moves_rejected_to_wasted_and_nothing_else"""
        lot = self._lot("100")
        raw_before = inv.raw_available_kg(self.cotton)
        waste_before = inv.waste_available_kg(self.cotton)
        self.assertEqual(self._stock_line()["rejected_kg"], "100.000")

        waste = self._convert_ok(lot)

        self.assertEqual(waste.quantity_kg, Decimal("100.000"))
        self.assertEqual(waste.inward_raw_material, lot)
        self.assertEqual(waste.reason, "Rejected lot SUP-1 (Farmer Joe)")
        self.assertEqual(waste.created_by, self.admin)
        self.assertEqual(
            self._raw_deltas(StockEventType.REJECTED_TO_WASTE),
            (Decimal("-100"), Decimal("100"), Decimal("0")),
        )
        self.assertEqual(inv.raw_available_kg(self.cotton), raw_before)
        self.assertEqual(inv.waste_available_kg(self.cotton), waste_before + 100)
        line = self._stock_line()
        self.assertEqual(line["rejected_kg"], "0.000")
        self.assertEqual(line["wasted_kg"], "100.000")
        self.assertEqual(Decimal(line["available_kg"]), raw_before)
        self._assert_ledger()

        restored = self._restore(waste)

        self.assertEqual(restored.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            self._raw_deltas(StockEventType.WASTE_TO_REJECTED),
            (Decimal("100"), Decimal("-100"), Decimal("0")),
        )
        self.assertEqual(inv.raw_available_kg(self.cotton), raw_before)
        self.assertEqual(inv.waste_available_kg(self.cotton), waste_before)
        self.assertEqual(self._stock_line()["rejected_kg"], "100.000")
        self._assert_ledger()

    def test_a_restored_lot_can_be_converted_again(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_a_restored_lot_can_be_converted_again"""
        lot = self._lot("40")
        self._restore(self._convert_ok(lot))

        again = self._convert_ok(lot, reason="second time")

        self.assertEqual(again.reason, "second time")
        self.assertEqual(RawMaterialWaste.objects.filter(inward_raw_material=lot).count(), 1)
        self._assert_ledger()

    def test_report_available_does_not_move_across_both_events(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_report_available_does_not_move_across_both_events"""
        lot = self._lot("100")
        StockEventLine.objects.all().delete()
        StockEvent.objects.all().delete()
        StockLedgerOperations.seed_ledger()
        today = indian_now().date()
        before = product_ledger_rows(self.cotton, today, today)[-1]["raw_material"]

        waste = self._convert_ok(lot)
        self._restore(waste)
        self._convert_ok(lot)

        rows = product_ledger_rows(self.cotton, today, today)
        events = [r for r in rows if r["event"] in ("REJECTED_TO_WASTE", "WASTE_TO_REJECTED")]
        self.assertEqual(
            [r["event"] for r in events],
            ["REJECTED_TO_WASTE", "WASTE_TO_REJECTED", "REJECTED_TO_WASTE"],
        )
        for row in events:
            self.assertEqual(row["raw_material"]["change"]["available"], "0.000")
        self.assertEqual(events[0]["raw_material"]["change"]["rejected"], "-100.000")
        self.assertEqual(events[0]["raw_material"]["change"]["wasted"], "100.000")
        self.assertEqual(events[0]["source"]["kind"], "raw_material_waste")
        self.assertEqual(events[0]["source"]["inward_raw_material"]["lot_no"], "SUP-1")
        self.assertEqual(rows[-1]["raw_material"]["available"], before["available"])
        self._assert_ledger()

    def test_lot_payload_shows_its_waste_and_the_waste_payload_its_lot(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_lot_payload_shows_its_waste_and_the_waste_payload_its_lot"""
        lot = self._lot("25")
        response = self._convert(lot)
        self.assertEqual(
            response.data["inward_raw_material"],
            {"public_id": lot.public_id, "lot_no": "SUP-1", "farmer_name": "Farmer Joe"},
        )

        lots = self.client.get(LOTS_URL).data["results"]
        row = next(r for r in lots if r["public_id"] == lot.public_id)
        self.assertEqual(row["waste"], {"public_id": response.data["public_id"]})

        self._restore(RawMaterialWaste.objects.get(public_id=response.data["public_id"]))
        lots = self.client.get(LOTS_URL).data["results"]
        row = next(r for r in lots if r["public_id"] == lot.public_id)
        self.assertIsNone(row["waste"])

    # -- refusals ---------------------------------------------------------------

    def test_a_converted_lot_is_not_bookable_or_listed_for_rejected_orders(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_a_converted_lot_is_not_bookable_or_listed_for_rejected_orders"""
        lot = self._lot("100")
        self.assertIn(lot, inv.bookable_rejected_lots())
        self._convert_ok(lot)
        self.assertNotIn(lot, inv.bookable_rejected_lots())

        listed = self.client.get(PARTY_LOTS_URL.format(party_id=self.party.id))
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.content)
        self.assertNotIn(lot.public_id, str(listed.data))

    def test_a_lot_with_kg_on_a_rejected_order_cannot_be_converted(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_a_lot_with_kg_on_a_rejected_order_cannot_be_converted"""
        lot = self._lot("100")
        address = self.acme.client_addresses.get(address__city=self.city)
        booked = self.client.post(
            CREATE_REJECTED_URL,
            {
                "client_public_id": self.acme.public_id,
                "client_address_id": address.id,
                "from_city_id": self.city.id,
                "driver_name": "Ramesh Driver",
                "driver_number": "9876500009",
                "vehicle_number": "GJ05AB1234",
                "items": [
                    {
                        "inward_raw_material_public_id": lot.public_id,
                        "quantity_kg": "10",
                        "negotiated_selling_price": "10.00",
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(booked.status_code, status.HTTP_201_CREATED, booked.data)

        response = self._convert(lot)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(RawMaterialWaste.objects.filter(inward_raw_material=lot).exists())
        self._assert_ledger()

    def test_converting_twice_an_in_use_lot_or_an_unreached_lot_is_refused(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_converting_twice_an_in_use_lot_or_an_unreached_lot_is_refused"""
        lot = self._lot("100")
        self._convert_ok(lot)
        self.assertEqual(self._convert(lot).status_code, status.HTTP_400_BAD_REQUEST)

        in_use = self._lot("10", lot_no="SUP-2", verdict="Pass")
        self.assertEqual(self._convert(in_use).status_code, status.HTTP_400_BAD_REQUEST)

        future = self._lot("10", lot_no="SUP-3")
        InwardRawMaterial.objects.filter(pk=future.pk).update(
            effective_date=indian_now().date() + timedelta(days=2)
        )
        self.assertEqual(self._convert(future).status_code, status.HTTP_400_BAD_REQUEST)
        # The ORM write above bypassed the ledger; put the lot back before it is checked.
        InwardRawMaterial.objects.filter(pk=future.pk).update(effective_date=future.effective_date)

        count = RawMaterialWaste.objects.filter(inward_raw_material__isnull=False).count()
        self.assertEqual(count, 1)

    def test_a_frozen_product_is_refused(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_a_frozen_product_is_refused"""
        lot = self._lot("100")
        Product.objects.filter(pk=self.cotton.pk).update(is_usable=False)

        self.assertEqual(self._convert(lot).status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_converted_lot_cannot_leave_rejected(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_a_converted_lot_cannot_leave_rejected"""
        lot = self._lot("100")
        waste = self._convert_ok(lot)

        deleted = self.client.delete(LOT_URL.format(public_id=lot.public_id))
        self.assertEqual(deleted.status_code, status.HTTP_400_BAD_REQUEST)

        revert = {"status": "Lab Testing"}
        reverted = self.client.patch(LOT_URL.format(public_id=lot.public_id), revert, format="json")
        self.assertEqual(reverted.status_code, status.HTTP_400_BAD_REQUEST)

        lot.refresh_from_db()
        with self.assertRaises(ValidationError):
            update_lab_test(lot, {"result": "Pass"}, self.admin)

        # Restored, the lot may leave Rejected again.
        self._restore(waste)
        reverted = self.client.patch(LOT_URL.format(public_id=lot.public_id), revert, format="json")
        self.assertEqual(reverted.status_code, status.HTTP_200_OK, reverted.data)
        self._assert_ledger()

    def test_a_converted_waste_row_cannot_be_edited_at_all(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_a_converted_waste_row_cannot_be_edited_at_all"""
        waste = self._convert_ok(self._lot("100"))
        url = WASTE_URL.format(public_id=waste.public_id)

        for body in ({"quantity_kg": "120"}, {"quantity_kg": "100"}, {"reason": "mouldy"}):
            refused = self.client.patch(url, body, format="json")
            self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST, body)

        waste.refresh_from_db()
        self.assertEqual(waste.quantity_kg, Decimal("100.000"))
        self.assertEqual(waste.reason, "Rejected lot SUP-1 (Farmer Joe)")
        self._assert_ledger()

    def test_restore_is_refused_when_the_waste_is_on_a_waste_order(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_restore_is_refused_when_the_waste_is_on_a_waste_order"""
        waste = self._convert_ok(self._lot("100"))
        create_waste_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.get(address__city=self.city).address,
            actor=self.admin,
            items=[
                {
                    "product": self.cotton,
                    "quantity_kg": Decimal("60"),
                    "negotiated_selling_price": Decimal("3"),
                }
            ],
        )

        response = self._restore(waste)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        waste.refresh_from_db()
        self.assertFalse(waste.is_deleted)
        self._assert_ledger()

    # -- godown ---------------------------------------------------------------

    def _godown_client(self, user) -> APIClient:
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    def test_the_godown_manager_can_convert_and_restore(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_the_godown_manager_can_convert_and_restore"""
        lot = self._lot("100")
        godown = User.objects.get(phone_number="3333333333")
        client = self._godown_client(godown)

        response = client.post(GODOWN_CONVERT_URL.format(public_id=lot.public_id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        waste = RawMaterialWaste.objects.get(public_id=response.data["public_id"])
        self.assertEqual(waste.created_by, godown)
        deleted = client.delete(GODOWN_WASTE_URL.format(public_id=waste.public_id))
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self._assert_ledger()

    def test_a_sales_person_cannot_convert_on_either_side(self):
        """tests/test_rejected_lot_waste.py::RejectedLotWasteTest::test_a_sales_person_cannot_convert_on_either_side"""
        lot = self._lot("100")
        self.clear_auth()
        self.login_as(self.sales_person)
        web = self._convert(lot)
        godown = self._godown_client(self.sales_person).post(
            GODOWN_CONVERT_URL.format(public_id=lot.public_id), {}, format="json"
        )

        self.assertIn(web.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertIn(godown.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertFalse(RawMaterialWaste.objects.filter(inward_raw_material=lot).exists())
