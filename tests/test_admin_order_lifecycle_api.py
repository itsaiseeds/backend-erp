"""Sales-admin order lifecycle: the six verb endpoints.

``verify-order`` / ``unverify-order``, ``dispatch-order`` / ``revert-dispatch``,
``hold-order`` and ``reject-order`` -- each action and its reversal, plus the
status guards that decide which orders a verb may be applied to.

The gates themselves (admin role, stock completeness, availability arithmetic)
are domain behaviour proven in ``tests/test_order_model.py`` and
``tests/test_inventory_operations.py``; what is asserted here is the endpoints'
own wiring -- the state machine, the HTTP status mapping and the payload.
Authentication and role gating are proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import create_client_with_details
from aggregator.models import (
    City,
    Country,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import create_order
from authentication.models import Admin, SalesPerson
from common.models import indian_now
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
VERIFY_URL = "/api/sales-admin/verify-order/{public_id}"
UNVERIFY_URL = "/api/sales-admin/unverify-order/{public_id}"
DISPATCH_URL = "/api/sales-admin/dispatch-order/{public_id}"
REVERT_URL = "/api/sales-admin/revert-dispatch/{public_id}"
HOLD_URL = "/api/sales-admin/hold-order/{public_id}"
REJECT_URL = "/api/sales-admin/reject-order/{public_id}"


class SalesAdminOrderLifecycleApiTest(WebApiTestCase):
    """Cover every lifecycle verb, its reversal and its status guard.

    tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.other_city = City.objects.get(name="Ahmedabad", state=cls.state)

        cls.admin_user = User.objects.create_user(
            phone_number="9000000601",
            name="Stock Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=cls.admin_user, created_by=cls.superuser, can_update_stock_count=True
        )

        cls.sales_person = User.objects.create_user(
            phone_number="9000000602",
            name="Sales One",
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

    def _count_stock(self, bags=400):
        """Count every packaging, including the dml.sql seed rows.

        ``is_stock_count_complete`` covers the whole catalogue, so a partial
        count would block verification for reasons unrelated to the test.
        """
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), bags),
            actor=self.admin_user,
        )

    def _order(self, quantity=2, *, by_agency=False):
        """Book an order. ``by_agency`` attaches the client's transport agency,
        which is what makes it an agency rather than a private dispatch."""
        agency = (
            self.acme.client_transport_agencies.first().transport_agency
            if by_agency
            else None
        )
        return create_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.first().address,
            actor=self.sales_person,
            items=[{"product_packaging": self.bag, "quantity": quantity}],
            transport_agency=agency,
        )

    def _post(self, url, order, body=None):
        return self.client.post(
            url.format(public_id=order.public_id), body or {}, format="json"
        )

    def _dispatch_body(self, **overrides):
        """The one body every dispatch takes, whichever kind the order is.

        ``items`` carries a lot number per line and must cover the order; every
        order booked here has the single ``self.bag`` line.
        """
        body = {
            "from_city_id": self.city.id,
            "driver_name": "Ramesh Driver",
            "driver_number": "9876500002",
            "vehicle_number": "GJ05AB1234",
            "items": [
                {
                    "product_packaging_public_id": self.bag.public_id,
                    "lot_number": "LOT-2026-01",
                }
            ],
        }
        body.update(overrides)
        return body

    def _verified_order(self, quantity=2, *, by_agency=False):
        order = self._order(quantity, by_agency=by_agency)
        self._count_stock()
        response = self._post(VERIFY_URL, order)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        return order

    def _dispatched_order(self):
        order = self._verified_order(by_agency=True)
        response = self._post(DISPATCH_URL, order, self._dispatch_body())
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        return order

    def _assert_refused(self, response, fragment):
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )
        self.assertIn(fragment, response.data["detail"])

    # -- verify ---------------------------------------------------------------

    def test_verify_confirms_the_order_and_records_the_admin(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_verify_confirms_the_order_and_records_the_admin"""
        order = self._order()
        self._count_stock()

        response = self._post(VERIFY_URL, order)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "CONFIRMED")
        self.assertIsNotNone(response.data["verified_at"])
        # The response is the full detail payload, client and all.
        self.assertEqual(response.data["client"]["company_name"], "Acme Seeds")

        order.refresh_from_db()
        self.assertEqual(order.verified_by, self.admin_user)
        self.assertIsNotNone(order.verified_at)

    def test_verify_is_allowed_from_booked_under_review_and_on_hold(self):
        """The three verifiable starting points, one subTest each.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_verify_is_allowed_from_booked_under_review_and_on_hold
        """
        self._count_stock()
        cases = [
            ("booked", None),
            ("on hold", StatusIds.ON_HOLD),
            ("under review", StatusIds.UNDER_REVIEW),
        ]
        for label, start in cases:
            with self.subTest(status=label):
                order = self._order(quantity=1)
                if start is not None:
                    order.status_id = start
                    order.save(update_fields=["status", "updated_at"])

                response = self._post(VERIFY_URL, order)

                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.data
                )
                self.assertEqual(response.data["status"], "CONFIRMED")

    def test_verifying_an_already_verified_order_is_rejected(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_verifying_an_already_verified_order_is_rejected"""
        order = self._verified_order()

        self._assert_refused(self._post(VERIFY_URL, order), "already verified")

    def test_a_rejected_order_can_never_be_verified(self):
        """Rejection is terminal.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_a_rejected_order_can_never_be_verified
        """
        order = self._order()
        self._count_stock()
        self._post(REJECT_URL, order)
        order.refresh_from_db()

        self._assert_refused(
            self._post(VERIFY_URL, order), "Cannot verify an order that is REJECTED"
        )

    def test_a_shortfall_blocks_verification_and_writes_nothing(self):
        """The atomicity assertion: a refused verification leaves the order alone.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_a_shortfall_blocks_verification_and_writes_nothing
        """
        order = self._order(quantity=5)
        self._count_stock(bags=2)

        response = self._post(VERIFY_URL, order)

        self._assert_refused(response, "Not enough stock")
        self.assertIn(self.bag.public_id, response.data["detail"])
        order.refresh_from_db()
        self.assertEqual(order.status.code, "BOOKED")
        self.assertIsNone(order.verified_by_id)
        self.assertIsNone(order.verified_at)

    def test_verification_is_blocked_without_a_stock_count(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_verification_is_blocked_without_a_stock_count"""
        order = self._order()

        self._assert_refused(self._post(VERIFY_URL, order), "stock count is incomplete")

    # -- unverify -------------------------------------------------------------

    def test_unverify_returns_the_order_to_under_review(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_unverify_returns_the_order_to_under_review"""
        order = self._verified_order()

        response = self._post(UNVERIFY_URL, order)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "UNDER_REVIEW")
        self.assertIsNone(response.data["verified_at"])
        order.refresh_from_db()
        self.assertIsNone(order.verified_by_id)

    def test_an_unverified_order_can_be_verified_again(self):
        """The round trip -- which is why UNDER_REVIEW is verifiable at all.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_an_unverified_order_can_be_verified_again
        """
        order = self._verified_order()
        self._post(UNVERIFY_URL, order)
        order.refresh_from_db()

        response = self._post(VERIFY_URL, order)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "CONFIRMED")

    def test_unverifying_an_unconfirmed_order_is_refused(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_unverifying_an_unconfirmed_order_is_refused"""
        order = self._order()

        self._assert_refused(
            self._post(UNVERIFY_URL, order), "Cannot unverify an order that is BOOKED"
        )

    # -- dispatch -------------------------------------------------------------

    def test_an_order_with_an_agency_dispatches_by_agency(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_an_order_with_an_agency_dispatches_by_agency"""
        order = self._verified_order(by_agency=True)

        response = self._post(DISPATCH_URL, order, self._dispatch_body())

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "DISPATCHED")
        self.assertEqual(response.data["dispatch_mode"], "AGENCY")
        order.refresh_from_db()
        self.assertIsNotNone(order.dispatch_details_id)
        self.assertIsNone(order.private_dispatch_details_id)
        dispatch = order.dispatch_details
        self.assertEqual(dispatch.driver_name, "Ramesh Driver")
        self.assertEqual(dispatch.driver_number, "9876500002")
        self.assertEqual(dispatch.vehicle_number, "GJ05AB1234")
        # The transporter issues the consignment note later.
        self.assertEqual(dispatch.lr_number, "")

    def test_an_order_without_an_agency_dispatches_privately(self):
        """The same body; only the table it lands in differs.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_an_order_without_an_agency_dispatches_privately
        """
        order = self._verified_order()

        response = self._post(DISPATCH_URL, order, self._dispatch_body())

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "DISPATCHED")
        self.assertEqual(response.data["dispatch_mode"], "PRIVATE")
        order.refresh_from_db()
        self.assertIsNotNone(order.private_dispatch_details_id)
        self.assertIsNone(order.dispatch_details_id)
        dispatch = order.private_dispatch_details
        self.assertEqual(dispatch.driver_name, "Ramesh Driver")
        self.assertEqual(dispatch.vehicle_number, "GJ05AB1234")

    def test_the_date_and_destination_are_derived_not_sent(self):
        """Today, and the city of the order's own delivery address.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_the_date_and_destination_are_derived_not_sent
        """
        order = self._verified_order()

        response = self._post(DISPATCH_URL, order, self._dispatch_body())

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        dispatch = order.private_dispatch_details
        self.assertEqual(dispatch.dispatch_date, indian_now().date())
        # The client's address is in Surat, so that is where it is going.
        self.assertEqual(dispatch.to_city, self.city)
        self.assertEqual(dispatch.from_city, self.city)

    def test_only_a_verified_order_can_be_dispatched(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_only_a_verified_order_can_be_dispatched"""
        order = self._order()

        self._assert_refused(
            self._post(DISPATCH_URL, order, self._dispatch_body()),
            "Cannot dispatch an order that is BOOKED",
        )
        order.refresh_from_db()
        self.assertIsNone(order.private_dispatch_details_id)

    def test_every_dispatch_field_is_mandatory(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_every_dispatch_field_is_mandatory"""
        order = self._verified_order()
        required = (
            "from_city_id",
            "driver_name",
            "driver_number",
            "vehicle_number",
            "items",
        )

        for field in required:
            with self.subTest(missing=field):
                body = self._dispatch_body()
                del body[field]

                self._assert_refused(
                    self._post(DISPATCH_URL, order, body), f"{field} is required."
                )

    def test_a_malformed_driver_number_is_rejected(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_a_malformed_driver_number_is_rejected"""
        order = self._verified_order()

        response = self._post(
            DISPATCH_URL, order, self._dispatch_body(driver_number="12345")
        )

        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data
        )

    # -- the challan the dispatch writes --------------------------------------

    def test_dispatching_writes_the_challan_and_its_lot_numbers(self):
        """The DispatchEntry snapshots the receiver; its lines carry the lots.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_dispatching_writes_the_challan_and_its_lot_numbers
        """
        order = self._verified_order(by_agency=True)

        response = self._post(DISPATCH_URL, order, self._dispatch_body())

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        entry = order.dispatch_entry
        self.assertTrue(entry.public_id.startswith("DE-"))
        self.assertEqual(entry.dispatch_details_id, order.dispatch_details_id)
        self.assertFalse(entry.is_private)
        self.assertEqual(entry.client_id, self.acme.pk)
        self.assertEqual(entry.client_address_id, order.delivery_address_id)
        # The receiver is snapshotted from the client's primary contact.
        self.assertEqual(entry.contact_name, "Ramesh")
        self.assertEqual(entry.contact_number, "9876500001")
        self.assertEqual(entry.dispatch_date, indian_now().date())
        self.assertEqual(entry.vehicle_number, "GJ05AB1234")

        line = entry.items.get()
        self.assertEqual(line.product_packaging_id, self.bag.pk)
        self.assertEqual(line.lot_number, "LOT-2026-01")
        self.assertEqual(line.quantity, 2)
        self.assertEqual(line.negotiated_selling_price, Decimal("1000.00"))

    def test_a_private_dispatch_writes_a_challan_with_no_transporter(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_a_private_dispatch_writes_a_challan_with_no_transporter"""
        order = self._verified_order()

        response = self._post(DISPATCH_URL, order, self._dispatch_body())

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        entry = order.dispatch_entry
        self.assertIsNone(entry.dispatch_details_id)
        self.assertTrue(entry.is_private)
        self.assertEqual(entry.lr_number, "")

    def test_a_lot_number_is_required_for_every_line(self):
        """Missing, unknown and duplicated packagings are each refused.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_a_lot_number_is_required_for_every_line
        """
        order = self._verified_order()
        lot = {"product_packaging_public_id": self.bag.public_id, "lot_number": "L1"}
        stranger = {"product_packaging_public_id": "PP-NOTONORDER", "lot_number": "L2"}
        cases = (
            ([stranger], "No lot number for"),
            ([lot, stranger], "Not on this order"),
            ([lot, lot], "listed twice"),
        )

        for items, fragment in cases:
            with self.subTest(items=items):
                self._assert_refused(
                    self._post(DISPATCH_URL, order, self._dispatch_body(items=items)),
                    fragment,
                )

        order.refresh_from_db()
        self.assertFalse(hasattr(order, "dispatch_entry"))

    def test_re_dispatching_rewrites_the_same_challan(self):
        """One order, one DE-... -- reverting and dispatching again reuses it.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_re_dispatching_rewrites_the_same_challan
        """
        order = self._dispatched_order()
        first = order.dispatch_entry
        original_public_id = first.public_id

        self._post(REVERT_URL, order)
        order.refresh_from_db()
        response = self._post(
            DISPATCH_URL,
            order,
            self._dispatch_body(
                vehicle_number="GJ05ZZ9999",
                items=[
                    {
                        "product_packaging_public_id": self.bag.public_id,
                        "lot_number": "LOT-2026-02",
                    }
                ],
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        entry = order.dispatch_entry
        self.assertEqual(entry.public_id, original_public_id)
        self.assertEqual(entry.vehicle_number, "GJ05ZZ9999")
        self.assertEqual(entry.items.get().lot_number, "LOT-2026-02")
        # A new journey gets a new DispatchDetails row, so the LR starts blank.
        self.assertEqual(entry.lr_number, "")

    # -- revert dispatch ------------------------------------------------------

    def test_revert_dispatch_returns_the_order_to_confirmed(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_revert_dispatch_returns_the_order_to_confirmed"""
        order = self._dispatched_order()

        response = self._post(REVERT_URL, order)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "CONFIRMED")
        order.refresh_from_db()
        self.assertIsNone(order.actual_delivery_date)

    def test_reverting_a_dispatch_that_never_happened_is_refused(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_reverting_a_dispatch_that_never_happened_is_refused"""
        order = self._verified_order()

        self._assert_refused(
            self._post(REVERT_URL, order),
            "Cannot revert the dispatch of an order that is CONFIRMED",
        )

    # -- hold and reject ------------------------------------------------------

    def test_holding_a_confirmed_order_releases_its_reserved_stock(self):
        """The bags come back because reservations are derived from the status.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_holding_a_confirmed_order_releases_its_reserved_stock
        """
        order = self._verified_order(quantity=3)
        self.assertEqual(inv.available_bags(self.bag), 397)

        response = self._post(HOLD_URL, order)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "ON_HOLD")
        self.assertEqual(inv.available_bags(self.bag), 400)

    def test_hold_and_reject_from_each_allowed_status(self):
        """tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_hold_and_reject_from_each_allowed_status"""
        self._count_stock()
        cases = [
            ("hold a booked order", HOLD_URL, None, "ON_HOLD"),
            ("hold an order under review", HOLD_URL, StatusIds.UNDER_REVIEW, "ON_HOLD"),
            ("reject a booked order", REJECT_URL, None, "REJECTED"),
            ("reject a held order", REJECT_URL, StatusIds.ON_HOLD, "REJECTED"),
        ]
        for label, url, start, expected in cases:
            with self.subTest(case=label):
                order = self._order(quantity=1)
                if start is not None:
                    order.status_id = start
                    order.save(update_fields=["status", "updated_at"])

                response = self._post(url, order)

                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.data
                )
                self.assertEqual(response.data["status"], expected)

    def test_a_dispatched_order_can_be_neither_held_nor_rejected(self):
        """The goods have left, so the status must keep saying so.

        tests/test_admin_order_lifecycle_api.py::SalesAdminOrderLifecycleApiTest::test_a_dispatched_order_can_be_neither_held_nor_rejected
        """
        order = self._dispatched_order()

        for label, url, action in (
            ("hold", HOLD_URL, "hold"),
            ("reject", REJECT_URL, "reject"),
        ):
            with self.subTest(verb=label):
                self._assert_refused(
                    self._post(url, order),
                    f"Cannot {action} an order that is DISPATCHED",
                )
