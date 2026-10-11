"""``PATCH /android/api/v1/edit-order/<public_id>`` -- a sales person edits a BOOKED order.

Authentication and role gating are proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import status

from aggregator.models import Order, StatusIds
from aggregator.models.Status import Status
from tests.android.common import AndroidApiTestCase
from tests.android.test_bag_orders import CREATE_ORDER_URL, BagOrderFixture

EDIT_URL = "/android/api/v1/edit-order/{public_id}"


class AndroidEditOrderApiTest(BagOrderFixture, AndroidApiTestCase):
    """Owner-only, BOOKED-only edits, at list price.

    tests/android/test_edit_order.py::AndroidEditOrderApiTest
    """

    def _book(self, quantity=3):
        self.login_as(self.sales_person)
        response = self.client.post(
            CREATE_ORDER_URL,
            {
                "client_public_id": self.client_row.public_id,
                "client_address_id": self.address_link.id,
                "items": [
                    {"product_packaging_public_id": self.bag.public_id, "quantity": quantity}
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return Order.objects.get(public_id=response.data["public_id"])

    def _patch(self, order, body, actor=None):
        self.login_as(actor or self.sales_person)
        return self.client.patch(EDIT_URL.format(public_id=order.public_id), body, format="json")

    def test_the_owner_edits_items_agency_and_comments_at_list_price(self):
        order = self._book()

        response = self._patch(
            order,
            {
                "items": [
                    {"product_packaging_public_id": self.bag.public_id, "quantity": 5},
                    {"product_packaging_public_id": self.other_bag.public_id, "quantity": 1},
                ],
                "client_transport_agency_id": self.agency_link.id,
                "special_comments": "call first",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        order.refresh_from_db()
        lines = {line.product_packaging_id: line for line in order.items.all()}
        self.assertEqual(lines[self.bag.id].quantity, 5)
        self.assertEqual(lines[self.other_bag.id].negotiated_selling_price, Decimal("1100.00"))
        self.assertEqual(order.transport_agency, self.agency_link.transport_agency)
        self.assertIn("call first", order.special_comments)

    def test_a_price_cannot_be_sent(self):
        order = self._book()

        response = self._patch(
            order,
            {
                "items": [
                    {
                        "product_packaging_public_id": self.bag.public_id,
                        "quantity": 3,
                        "negotiated_selling_price": "1.00",
                    }
                ]
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(order.items.get().negotiated_selling_price, Decimal("1000.00"))

    def test_a_confirmed_order_is_refused(self):
        order = self._book()
        Order.objects.filter(pk=order.pk).update(status=Status.by_id(StatusIds.CONFIRMED))

        response = self._patch(order, {"special_comments": "late"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_another_sales_persons_order_is_unknown(self):
        order = self._book()

        response = self._patch(order, {"special_comments": "mine now"}, actor=self.other_sales_person)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_foreign_address_is_refused(self):
        order = self._book()

        response = self._patch(order, {"client_address_id": self.other_address_link.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        self.assertEqual(order.delivery_address, self.address_link.address)
