"""Sales-admin order editing: ``PATCH /api/sales-admin/edit-order/<public_id>``.

Covers partial updates, the declarative item-list replacement, and the rules
that refuse an edit. Authentication and role gating are proven once in
``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.ClientOperations import create_client_with_details
from aggregator.models import (
    City,
    Country,
    OrderItem,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import (
    attach_private_dispatch_details,
    create_order,
    update_order_status,
)
from authentication.models import Admin, SalesPerson
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
EDIT_URL = "/api/sales-admin/edit-order/{public_id}"


class SalesAdminOrderEditApiTest(WebApiTestCase):
    """Cover correcting an order and the edits that are refused.

    tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """One sales person, two clients (so a foreign link id exists), two bags."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)

        cls.admin_user = User.objects.create_user(
            phone_number="9000000501",
            name="Sales Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)

        cls.sales_person = User.objects.create_user(
            phone_number="9000000502",
            name="Sales One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(
            user=cls.sales_person, city=cls.city, created_by=cls.superuser
        )

        cls.acme = cls._client("Acme Seeds", "27AAPFU0939F1ZV")
        cls.other = cls._client("Other Seeds", "27AAPFU0939F1ZB")

        cls.alpha_bag = cls._bag("Alpha Seed", Decimal("1000.00"), packets=10)
        cls.beta_bag = cls._bag("Beta Seed", Decimal("500.00"), packets=5)

    @classmethod
    def _client(cls, company_name, gst):
        return create_client_with_details(
            company_name=company_name,
            company_phone="9876543210",
            gst_number=gst,
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
            transport_agencies=[{"name": f"{company_name} Transport"}],
            actor=cls.sales_person,
        )

    @classmethod
    def _bag(cls, product_name, price, *, packets):
        product = Product.objects.create(
            name=product_name,
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )
        return ProductPackaging.objects.create(
            product=product,
            packet_weight=Decimal("1.000"),
            packets=packets,
            selling_price=price,
            created_by=cls.superuser,
        )

    def setUp(self):
        super().setUp()
        self.order = create_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.first().address,
            actor=self.sales_person,
            items=[{"product_packaging": self.alpha_bag, "quantity": 2}],
        )
        self.login_as(self.admin_user)

    # -- helpers --------------------------------------------------------------

    def _patch(self, body, order=None):
        return self.client.patch(
            EDIT_URL.format(public_id=(order or self.order).public_id),
            body,
            format="json",
        )

    def _line(self, packaging, quantity, price=None):
        line = {
            "product_packaging_public_id": packaging.public_id,
            "quantity": quantity,
        }
        if price is not None:
            line["negotiated_selling_price"] = price
        return line

    # -- partial updates ------------------------------------------------------

    def test_only_the_fields_sent_are_changed(self):
        """An absent field is left alone -- no serializer default rewrites a column.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_only_the_fields_sent_are_changed
        """
        response = self._patch(
            {"special_comments": "Deliver before noon", "expected_delivery_date": "2026-10-01"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["special_comments"], "Deliver before noon")
        self.assertEqual(response.data["expected_delivery_date"], "2026-10-01")

        self.order.refresh_from_db()
        self.assertEqual(self.order.status.code, "BOOKED")
        self.assertEqual(self.order.created_by, self.sales_person)
        self.assertIsNone(self.order.verified_by_id)
        self.assertEqual(self.order.items.count(), 1)
        self.assertIsNone(self.order.transport_agency_id)

    def test_the_status_can_be_changed(self):
        """tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_the_status_can_be_changed"""
        response = self._patch({"status": "ON_HOLD"})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status.code, "ON_HOLD")

    def test_the_transport_agency_can_be_set_and_cleared(self):
        """Setting an agency makes it an AGENCY dispatch; null returns it to PRIVATE.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_the_transport_agency_can_be_set_and_cleared
        """
        link = self.acme.client_transport_agencies.first()

        attached = self._patch({"client_transport_agency_id": link.id})
        self.assertEqual(attached.status_code, status.HTTP_200_OK, attached.data)
        self.assertEqual(attached.data["dispatch_mode"], "AGENCY")
        self.assertEqual(attached.data["transport_agency"]["name"], "Acme Seeds Transport")

        cleared = self._patch({"client_transport_agency_id": None})
        self.assertEqual(cleared.status_code, status.HTTP_200_OK, cleared.data)
        self.assertEqual(cleared.data["dispatch_mode"], "PRIVATE")
        self.assertIsNone(cleared.data["transport_agency"])

    def test_special_comments_are_appended_never_replaced(self):
        """Each remark is added as a new line, so nothing an earlier one said is lost.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_special_comments_are_appended_never_replaced
        """
        first = self._patch({"special_comments": "Call before delivery"})
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
        self.assertEqual(first.data["special_comments"], "Call before delivery")

        second = self._patch({"special_comments": "Client rescheduled to Friday"})

        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(
            second.data["special_comments"],
            "Call before delivery\nClient rescheduled to Friday",
        )

    def test_a_blank_comment_adds_nothing(self):
        """A blank remark is a no-op, not a blank line.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_a_blank_comment_adds_nothing
        """
        self._patch({"special_comments": "Call before delivery"})

        response = self._patch({"special_comments": "   "})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["special_comments"], "Call before delivery")

    def test_the_client_cannot_be_changed(self):
        """An order stays with the client it was booked for.

        Moving it would invalidate its delivery address, its agency and the
        prices its lines were negotiated at, so there is no client field --
        and the address/agency link ids are scoped to the order's own client.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_the_client_cannot_be_changed
        """
        bodies = [
            ("client_public_id", {"client_public_id": self.other.public_id}),
            ("client_id", {"client_id": self.other.id}),
            ("client", {"client": self.other.id}),
        ]
        for label, body in bodies:
            with self.subTest(field=label):
                response = self._patch({**body, "special_comments": "touched"})

                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.data
                )
                self.assertEqual(response.data["client"]["public_id"], self.acme.public_id)
                self.order.refresh_from_db()
                self.assertEqual(self.order.client, self.acme)

    # -- item list replacement ------------------------------------------------

    def test_one_patch_adds_drops_reprices_and_requantifies_lines(self):
        """The item list is a full declarative replacement.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_one_patch_adds_drops_reprices_and_requantifies_lines
        """
        response = self._patch(
            {
                "items": [
                    # alpha stays, at a new quantity and a negotiated price
                    self._line(self.alpha_bag, 3, "900.00"),
                    # beta is new
                    self._line(self.beta_bag, 2),
                ]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        lines = {
            item["packaging"]["public_id"]: item for item in response.data["items"]
        }
        self.assertEqual(set(lines), {self.alpha_bag.public_id, self.beta_bag.public_id})
        self.assertEqual(lines[self.alpha_bag.public_id]["quantity"], 3)
        self.assertEqual(
            lines[self.alpha_bag.public_id]["negotiated_selling_price"], "900.00"
        )
        # A new line defaults to the bag's own list price.
        self.assertEqual(
            lines[self.beta_bag.public_id]["negotiated_selling_price"], "500.00"
        )
        # 3 x 900 + 2 x 500
        self.assertEqual(response.data["total_amount"], "3700.00")

    def test_a_line_left_out_of_the_list_is_removed(self):
        """Omitting a line removes it; it is soft-deleted, never destroyed.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_a_line_left_out_of_the_list_is_removed
        """
        self._patch({"items": [self._line(self.alpha_bag, 1), self._line(self.beta_bag, 1)]})

        response = self._patch({"items": [self._line(self.alpha_bag, 1)]})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [item["packaging"]["public_id"] for item in response.data["items"]],
            [self.alpha_bag.public_id],
        )
        removed = OrderItem.all_objects.get(
            order=self.order, product_packaging=self.beta_bag
        )
        self.assertTrue(removed.is_deleted)
        self.assertEqual(removed.deleted_by, self.admin_user)
        self.assertFalse(
            OrderItem.objects.filter(
                order=self.order, product_packaging=self.beta_bag
            ).exists()
        )

    def test_re_adding_a_removed_line_restores_the_original_row(self):
        """The unique constraint covers soft-deleted rows, so a re-add must restore.

        Inserting a second line for the same packaging would violate
        ``uniq_orderitem_order_packaging`` and surface as a 500 rather than a
        validation error.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_re_adding_a_removed_line_restores_the_original_row
        """
        self._patch({"items": [self._line(self.alpha_bag, 1), self._line(self.beta_bag, 4)]})
        original_id = OrderItem.objects.get(
            order=self.order, product_packaging=self.beta_bag
        ).id

        self._patch({"items": [self._line(self.alpha_bag, 1)]})
        response = self._patch(
            {"items": [self._line(self.alpha_bag, 1), self._line(self.beta_bag, 7)]}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        restored = OrderItem.objects.get(
            order=self.order, product_packaging=self.beta_bag
        )
        self.assertEqual(restored.id, original_id)
        self.assertFalse(restored.is_deleted)
        self.assertIsNone(restored.deleted_by_id)
        self.assertEqual(restored.quantity, 7)
        self.assertEqual(
            OrderItem.all_objects.filter(
                order=self.order, product_packaging=self.beta_bag
            ).count(),
            1,
        )

    # -- refusals -------------------------------------------------------------

    def test_invalid_edits_are_rejected(self):
        """One subTest per rule, each a 400 that names the problem.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_invalid_edits_are_rejected
        """
        other_address = self.other.client_addresses.first()
        other_agency = self.other.client_transport_agencies.first()
        cases = [
            ("empty item list", {"items": []}, "at least one item"),
            (
                "the same bag twice",
                {"items": [self._line(self.alpha_bag, 1), self._line(self.alpha_bag, 2)]},
                "listed twice",
            ),
            (
                "zero quantity",
                {"items": [self._line(self.alpha_bag, 0)]},
                "Quantity must be at least 1",
            ),
            (
                "unknown bag",
                {"items": [{"product_packaging_public_id": "PP-NOPE", "quantity": 1}]},
                "Unknown product packaging",
            ),
            (
                "another client's address",
                {"client_address_id": other_address.id},
                "No such address for this client",
            ),
            (
                "another client's agency",
                {"client_transport_agency_id": other_agency.id},
                "No such transport agency for this client",
            ),
            (
                "confirming without verifying",
                {"status": "CONFIRMED"},
                "must record who verified it",
            ),
            (
                "dispatching without dispatch details",
                {"status": "DISPATCHED"},
                "Dispatch details are required",
            ),
        ]
        for label, body, fragment in cases:
            with self.subTest(case=label):
                response = self._patch(body)
                self.assertEqual(
                    response.status_code, status.HTTP_400_BAD_REQUEST, response.data
                )
                self.assertIn(fragment, response.data["detail"])

    def test_a_dispatched_order_refuses_every_edit(self):
        """Once the goods have left, the order is history.

        tests/test_admin_order_edit_api.py::SalesAdminOrderEditApiTest::test_a_dispatched_order_refuses_every_edit
        """
        dispatched = create_order(
            client=self.acme,
            delivery_address=self.acme.client_addresses.first().address,
            actor=self.sales_person,
            items=[{"product_packaging": self.alpha_bag, "quantity": 1}],
        )
        self._dispatch(dispatched)

        response = self._patch({"special_comments": "too late"}, order=dispatched)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("Cannot edit an order that is DISPATCHED", response.data["detail"])

    def _dispatch(self, order):
        """Move ``order`` to DISPATCHED through the domain layer.

        The order carries no transport agency, so it is a private dispatch --
        which kind it is follows from the order, never from the call.
        """
        attach_private_dispatch_details(
            order,
            dispatched_by=self.admin_user,
            dispatch_date="2026-09-13",
            from_city=self.city,
            to_city=self.city,
            driver_name="Ramesh Driver",
            driver_number="9876500002",
            vehicle_number="GJ05AB1234",
        )
        update_order_status(order, StatusIds.DISPATCHED)
