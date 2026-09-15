"""Recording an LR number, and the challan list it makes an order eligible for.

Two endpoints, one story: ``upload-lr-number`` records the consignment note a
transporter issues after collection, and ``dispatch-challans/`` lists exactly
those orders whose challan is complete because of it.

What the dispatch itself writes -- the ``DispatchEntry`` and its lot-numbered
lines -- is proven in ``tests/test_admin_order_lifecycle_api.py``, where
``dispatch-order`` lives. Authentication and role gating are proven once in
``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import create_client_with_details
from aggregator.CompanyDetails import COMPANY_DETAILS, DEFAULT_HSN_CODE
from aggregator.models import (
    City,
    Country,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.OrderOperations import create_order, mark_delivered
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
VERIFY_URL = "/api/sales-admin/verify-order/{public_id}"
DISPATCH_URL = "/api/sales-admin/dispatch-order/{public_id}"
REVERT_URL = "/api/sales-admin/revert-dispatch/{public_id}"
LR_URL = "/api/sales-admin/upload-lr-number/{public_id}"
CHALLANS_URL = "/api/sales-admin/dispatch-challans/"


class DispatchChallansApiTest(WebApiTestCase):
    """The LR endpoint and the challan list that depends on it.

    tests/test_dispatch_challans_api.py::DispatchChallansApiTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)

        cls.admin_user = User.objects.create_user(
            phone_number="9000000701",
            name="Challan Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=cls.admin_user, created_by=cls.superuser, can_update_stock_count=True
        )

        cls.sales_person = User.objects.create_user(
            phone_number="9000000702",
            name="Challan Sales",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(
            user=cls.sales_person, city=cls.city, created_by=cls.superuser
        )

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

        product = Product.objects.create(
            name="Alpha Seed",
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )
        cls.bag = ProductPackaging.objects.create(
            product=product,
            packet_weight=Decimal("1.000"),
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=cls.superuser,
        )

    def setUp(self):
        super().setUp()
        self.login_as(self.admin_user)

    # -- helpers --------------------------------------------------------------

    def _dispatched_order(self, *, by_agency=True, lot_number="LOT-2026-01"):
        """Book, verify and dispatch one order; return it at DISPATCHED."""
        agency = (
            self.acme.client_transport_agencies.first().transport_agency
            if by_agency
            else None
        )
        order = create_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.first().address,
            actor=self.sales_person,
            items=[{"product_packaging": self.bag, "quantity": 2}],
            transport_agency=agency,
        )
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), 400),
            actor=self.admin_user,
        )
        self._post(VERIFY_URL, order)
        self._post(
            DISPATCH_URL,
            order,
            {
                "from_city_id": self.city.id,
                "driver_name": "Ramesh Driver",
                "driver_number": "9876500002",
                "vehicle_number": "GJ05AB1234",
                "items": [
                    {
                        "product_packaging_public_id": self.bag.public_id,
                        "lot_number": lot_number,
                    }
                ],
            },
        )
        order.refresh_from_db()
        return order

    def _post(self, url, order, body=None):
        return self.client.post(
            url.format(public_id=order.public_id), body or {}, format="json"
        )

    def _upload_lr(self, order, lr_number="LR-12345"):
        return self._post(LR_URL, order, {"lr_number": lr_number})

    def _challans(self, **params):
        """The challan list over a window wide enough to hold today."""
        now = indian_now()
        query = {
            "start_date_time": (now - timedelta(days=1)).isoformat(),
            "end_date_time": (now + timedelta(days=1)).isoformat(),
        }
        query.update(params)
        return self.client.get(CHALLANS_URL, query)

    # -- upload-lr-number -----------------------------------------------------

    def test_the_lr_lands_on_the_dispatch_and_reads_through_the_challan(self):
        """tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_the_lr_lands_on_the_dispatch_and_reads_through_the_challan"""
        order = self._dispatched_order()

        response = self._upload_lr(order)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        self.assertEqual(order.dispatch_details.lr_number, "LR-12345")
        # Stored once, on the transporter's row; the challan reads it through.
        self.assertEqual(order.dispatch_entry.lr_number, "LR-12345")

    def test_a_private_dispatch_has_no_lr_to_record(self):
        """The rule the endpoint exists to enforce: no transporter, no note.

        tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_a_private_dispatch_has_no_lr_to_record
        """
        order = self._dispatched_order(by_agency=False)

        response = self._upload_lr(order)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertIn("our own vehicle", response.data["detail"])
        order.refresh_from_db()
        self.assertEqual(order.dispatch_entry.lr_number, "")

    def test_an_undispatched_order_has_no_lr_to_record(self):
        """tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_an_undispatched_order_has_no_lr_to_record"""
        order = create_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.first().address,
            actor=self.sales_person,
            items=[{"product_packaging": self.bag, "quantity": 1}],
        )

        response = self._upload_lr(order)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertIn("not been dispatched", response.data["detail"])

    def test_a_blank_lr_number_is_refused(self):
        """tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_a_blank_lr_number_is_refused"""
        order = self._dispatched_order()

        for body in ({}, {"lr_number": ""}, {"lr_number": "   "}):
            with self.subTest(body=body):
                response = self._post(LR_URL, order, body)

                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.data
                )
                self.assertIn("lr_number is required.", response.data["detail"])

    # -- dispatch-challans ----------------------------------------------------

    def test_the_date_window_is_required(self):
        """Unlike the order list: a challan list is always read for a period.

        tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_the_date_window_is_required
        """
        response = self.client.get(CHALLANS_URL)

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    def test_an_agency_order_is_listed_only_once_its_lr_is_recorded(self):
        """The transporter's note is part of that challan, so it waits for one.

        tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_an_agency_order_is_listed_only_once_its_lr_is_recorded
        """
        order = self._dispatched_order()

        before = self._challans()
        self.assertEqual(before.status_code, status.HTTP_200_OK, before.data)
        self.assertEqual(before.data["total_count"], 0)

        self._upload_lr(order)

        after = self._challans()
        self.assertEqual(after.data["total_count"], 1)
        self.assertEqual(
            after.data["results"][0]["order_public_id"], order.public_id
        )

    def test_a_private_dispatch_is_listed_without_any_lr(self):
        """No transporter means no note to wait for, so it is listed at once.

        tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_a_private_dispatch_is_listed_without_any_lr
        """
        order = self._dispatched_order(by_agency=False)

        response = self._challans()

        self.assertEqual(response.data["total_count"], 1)
        challan = response.data["results"][0]
        self.assertEqual(challan["order_public_id"], order.public_id)
        self.assertTrue(challan["dispatch"]["is_private"])
        self.assertEqual(challan["dispatch"]["lr_number"], "")

    def test_a_dispatch_outside_the_window_is_excluded(self):
        """tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_a_dispatch_outside_the_window_is_excluded"""
        order = self._dispatched_order()
        self._upload_lr(order)
        yesterday = indian_now() - timedelta(days=1)

        response = self._challans(
            start_date_time=(yesterday - timedelta(days=1)).isoformat(),
            end_date_time=yesterday.isoformat(),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["total_count"], 0)

    def test_reverting_a_dispatch_takes_the_challan_off_the_list(self):
        """The dispatch rows survive a revert, so the status is what excludes it.

        tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_reverting_a_dispatch_takes_the_challan_off_the_list
        """
        order = self._dispatched_order()
        self._upload_lr(order)
        self.assertEqual(self._challans().data["total_count"], 1)

        self._post(REVERT_URL, order)

        order.refresh_from_db()
        # The goods are back on the shelf, but the paperwork is untouched.
        self.assertEqual(order.status.code, "CONFIRMED")
        self.assertIsNotNone(order.dispatch_details_id)
        self.assertEqual(order.dispatch_entry.lr_number, "LR-12345")
        self.assertEqual(self._challans().data["total_count"], 0)

    def test_a_delivered_order_keeps_its_challan(self):
        """tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_a_delivered_order_keeps_its_challan"""
        order = self._dispatched_order()
        self._upload_lr(order)

        mark_delivered(order)

        self.assertEqual(self._challans().data["total_count"], 1)

    def test_a_challan_carries_every_block_needed_to_print_it(self):
        """tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_a_challan_carries_every_block_needed_to_print_it"""
        order = self._dispatched_order()
        self._upload_lr(order)

        challan = self._challans().data["results"][0]

        self.assertEqual(challan["our_details"], COMPANY_DETAILS)
        self.assertEqual(challan["hsn_code"], DEFAULT_HSN_CODE)

        receiver = challan["receiver_details"]
        self.assertEqual(receiver["company_name"], "Acme Seeds")
        self.assertEqual(receiver["gst_number"], "27AAPFU0939F1ZV")
        self.assertEqual(receiver["address"]["line_1"], "1 Ring Road")
        self.assertEqual(receiver["address"]["city"], "Surat")
        self.assertEqual(receiver["contact_person_name"], "Ramesh")
        self.assertEqual(receiver["contact_person_number"], "9876500001")

        dispatch = challan["dispatch"]
        self.assertTrue(dispatch["public_id"].startswith("DE-"))
        self.assertEqual(dispatch["lr_number"], "LR-12345")
        self.assertEqual(dispatch["vehicle_number"], "GJ05AB1234")
        self.assertEqual(dispatch["driver_name"], "Ramesh Driver")
        self.assertEqual(dispatch["from_city"], "Surat")
        self.assertEqual(dispatch["to_city"], "Surat")
        self.assertFalse(dispatch["is_private"])

        line = challan["items"][0]
        self.assertEqual(line["public_id"], self.bag.public_id)
        self.assertEqual(line["lot_number"], "LOT-2026-01")
        self.assertEqual(line["quantity"], 2)
        self.assertEqual(line["line_total"], "2000.00")
        self.assertEqual(challan["total_amount"], "2000.00")
        self.assertEqual(challan["total_packets"], 20)

    def test_the_financial_year_runs_april_to_march(self):
        """tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_the_financial_year_runs_april_to_march"""
        order = self._dispatched_order()
        self._upload_lr(order)
        today = indian_now().date()
        start = today.year if today.month >= 4 else today.year - 1

        challan = self._challans().data["results"][0]

        self.assertEqual(challan["financial_year"], f"{start}-{start + 1}")

    def test_re_dispatching_drops_the_order_back_out_of_the_list(self):
        """A new journey needs a new consignment note before it is a challan.

        tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_re_dispatching_drops_the_order_back_out_of_the_list
        """
        order = self._dispatched_order()
        self._upload_lr(order)
        self.assertEqual(self._challans().data["total_count"], 1)

        self._post(REVERT_URL, order)
        order.refresh_from_db()
        self._post(
            DISPATCH_URL,
            order,
            {
                "from_city_id": self.city.id,
                "driver_name": "Ramesh Driver",
                "driver_number": "9876500002",
                "vehicle_number": "GJ05AB1234",
                "items": [
                    {
                        "product_packaging_public_id": self.bag.public_id,
                        "lot_number": "LOT-2026-02",
                    }
                ],
            },
        )

        self.assertEqual(self._challans().data["total_count"], 0)

    def test_the_catalogues_offer_only_clients_and_cities_with_challans(self):
        """tests/test_dispatch_challans_api.py::DispatchChallansApiTest::test_the_catalogues_offer_only_clients_and_cities_with_challans"""
        order = self._dispatched_order()

        empty = {
            entry["filter"]: entry for entry in self._challans().data["available_filters"]
        }
        self.assertEqual(empty["client"]["options"], [])

        self._upload_lr(order)

        filters = {
            entry["filter"]: entry for entry in self._challans().data["available_filters"]
        }
        self.assertEqual(
            filters["client"]["options"],
            [{"value": self.acme.pk, "label": "Acme Seeds"}],
        )
        self.assertEqual(
            filters["city_id"]["options"],
            [{"value": self.city.pk, "label": "Surat"}],
        )
