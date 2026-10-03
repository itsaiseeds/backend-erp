"""Android dispatch challans: a sales person sees only the challans of orders they made.

Covers ``get-challans`` (the paginated list) and ``get-challan/<order_public_id>``
(one challan). The rule under test: **own orders only, and only while the order
is DISPATCHED or DELIVERED**. Authentication and the role gate are owned by
``tests/test_view_contracts.py``; the website's own list is covered by
``tests/test_dispatch_challans_api.py`` and is unchanged.

Run: bash scripts/run.sh test-serial tests/android/test_challans.py
"""

from __future__ import annotations

from datetime import timedelta

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import add_client_address, create_client
from aggregator.CustomOrderOperations import create_custom_order, dispatch_custom_order
from aggregator.OrderOperations import (
    create_order,
    dispatch_order,
    mark_delivered,
    revert_dispatch,
    verify_order,
)
from common.models import indian_now
from tests.stock_ledger_support import W1
from tests.test_return_orders import ReturnWorldTestCase

LIST_URL = "/android/api/v1/get-challans"
ONE_URL = "/android/api/v1/get-challan/{public_id}"


class AndroidChallanTest(ReturnWorldTestCase):
    """Own-orders-only challans for a sales person.

    tests/android/test_challans.py::AndroidChallanTest
    """

    def setUp(self):
        super().setUp()
        self.mine = self._android(self.sp_user)
        self.theirs = self._android(self.other_sp)

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _android(user) -> APIClient:
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    @staticmethod
    def _window(**extra) -> dict:
        now = indian_now()
        return {
            "start_date_time": (now - timedelta(days=1)).isoformat(),
            "end_date_time": (now + timedelta(days=1)).isoformat(),
            **extra,
        }

    def _listed(self, client=None, **params) -> set[str]:
        response = (client or self.mine).get(LIST_URL, self._window(**params))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        return {row["order_public_id"] for row in response.data["results"]}

    def _dispatch_for(self, client_obj, actor):
        """A DISPATCHED order booked by ``actor`` for ``client_obj``."""
        order = create_order(
            client=client_obj,
            delivery_address=self.address,
            actor=actor,
            items=[{"product_packaging": self.pp1, "quantity": 2}],
        )
        verify_order(order, self.su)
        dispatch_order(
            order,
            actor=self.su,
            from_city=self.city,
            driver_name="Ramesh",
            driver_number="9876500009",
            vehicle_number="GJ05AB1234",
            lot_numbers={self.pp1.public_id: "LOT-1"},
        )
        order.refresh_from_db()
        return order

    def _custom_order_dispatched(self):
        inv.record_loose_stocks(
            counts={(self.product, W1): 50}, actor=self.admin_user
        )
        order = create_custom_order(
            client=self.client_obj,
            delivery_address=self.address,
            actor=self.admin_user,
            items=[{"product": self.product, "packet_weight": W1, "packets": 5}],
        )
        dispatch_custom_order(
            order,
            actor=self.admin_user,
            from_city=self.city,
            driver_name="Ramesh",
            driver_number="9876500009",
            vehicle_number="GJ05AB1234",
            lot_numbers={(self.product.public_id, W1): "LOT-C"},
        )
        return order

    # -- the list -------------------------------------------------------------

    def test_the_list_holds_only_my_dispatched_and_delivered_orders(self):
        """Not other people's, not confirmed ones, not reverted ones, not custom orders.

        tests/android/test_challans.py::AndroidChallanTest::test_the_list_holds_only_my_dispatched_and_delivered_orders
        """
        dispatched = self.dispatched_order()
        delivered = self.dispatched_order()
        mark_delivered(delivered)
        self.order(self.pp1, 1)  # mine, but only CONFIRMED
        reverted = self.dispatched_order()
        revert_dispatch(reverted)
        theirs = self.dispatched_order(actor=self.other_sp)
        custom = self._custom_order_dispatched()

        seen = self._listed()

        self.assertEqual(seen, {dispatched.public_id, delivered.public_id})
        for excluded in (reverted, theirs, custom):
            self.assertNotIn(excluded.public_id, seen)
        # The other sales person sees theirs, and none of mine.
        self.assertEqual(self._listed(self.theirs), {theirs.public_id})

    def test_a_row_is_the_same_challan_the_website_prints(self):
        """Same envelope and numbers as ``challan_entry_payload`` for that order.

        tests/android/test_challans.py::AndroidChallanTest::test_a_row_is_the_same_challan_the_website_prints
        """
        from aggregator.DispatchOperations import challan_entry_payload

        order = self.dispatched_order()
        row = self.mine.get(LIST_URL, self._window()).data["results"][0]
        expected = challan_entry_payload(order.dispatch_entry)

        self.assertEqual(list(row), list(expected))
        self.assertEqual(row["dispatch"]["challan_number"], expected["dispatch"]["challan_number"])
        self.assertEqual(row["items"][0]["lot_number"], "LOT-1")
        self.assertEqual(row["order_public_id"], order.public_id)

    def test_the_window_is_required_and_the_status_filter_splits_the_list(self):
        """No window is a 400; ?status= separates dispatched from delivered; junk is a 400.

        tests/android/test_challans.py::AndroidChallanTest::test_the_window_is_required_and_the_status_filter_splits_the_list
        """
        dispatched = self.dispatched_order()
        delivered = self.dispatched_order()
        mark_delivered(delivered)

        self.assertEqual(
            self.mine.get(LIST_URL).status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertEqual(self._listed(status="DISPATCHED"), {dispatched.public_id})
        self.assertEqual(self._listed(status="DELIVERED"), {delivered.public_id})
        junk = self.mine.get(LIST_URL, self._window(status="CONFIRMED"))
        self.assertEqual(junk.status_code, status.HTTP_400_BAD_REQUEST, junk.content)

    def test_filter_options_offer_only_my_own_clients(self):
        """Another sales person's client never appears in my pickers (or filters).

        tests/android/test_challans.py::AndroidChallanTest::test_filter_options_offer_only_my_own_clients
        """
        self.dispatched_order()
        their_client = create_client(
            company_name="Other Co", gst_number="24AAACC1206D1ZM", actor=self.other_sp
        )
        add_client_address(their_client, self.address, self.other_sp, is_primary=True)
        theirs = self._dispatch_for(their_client, self.other_sp)

        page = self.mine.get(LIST_URL, self._window()).data
        client_filter = next(f for f in page["available_filters"] if f["filter"] == "client")
        values = {option["value"] for option in client_filter["options"]}
        self.assertEqual(values, {self.client_obj.public_id})

        # Asking for their client by id still returns nothing of theirs.
        forced = self.mine.get(LIST_URL, self._window(client=their_client.public_id))
        self.assertEqual(forced.status_code, status.HTTP_200_OK, forced.content)
        self.assertEqual(forced.data["results"], [])
        self.assertNotIn(theirs.public_id, self._listed())

    # -- one challan ------------------------------------------------------------

    def test_one_challan_is_returned_for_my_dispatched_or_delivered_order(self):
        """The payload equals the list row, before and after delivery.

        tests/android/test_challans.py::AndroidChallanTest::test_one_challan_is_returned_for_my_dispatched_or_delivered_order
        """
        order = self.dispatched_order()
        url = ONE_URL.format(public_id=order.public_id)

        shipped = self.mine.get(url)
        self.assertEqual(shipped.status_code, status.HTTP_200_OK, shipped.content)
        self.assertEqual(shipped.data["order_public_id"], order.public_id)
        row = self.mine.get(LIST_URL, self._window()).data["results"][0]
        self.assertEqual(shipped.data, row)

        mark_delivered(order)
        self.assertEqual(self.mine.get(url).status_code, status.HTTP_200_OK)

    def test_anything_that_is_not_my_dispatched_order_is_a_404(self):
        """Someone else's, not dispatched, reverted, a custom order, unknown: all 404.

        tests/android/test_challans.py::AndroidChallanTest::test_anything_that_is_not_my_dispatched_order_is_a_404
        """
        theirs = self.dispatched_order(actor=self.other_sp)
        confirmed = self.order(self.pp1, 1)
        reverted = self.dispatched_order()
        revert_dispatch(reverted)
        custom = self._custom_order_dispatched()

        cases = {
            "another sales person's order": theirs.public_id,
            "a confirmed order": confirmed.public_id,
            "a reverted dispatch": reverted.public_id,
            "a custom order": custom.public_id,
            "an unknown id": "ORD-DOESNOTEXIST",
        }
        for label, public_id in cases.items():
            with self.subTest(case=label):
                response = self.mine.get(ONE_URL.format(public_id=public_id))
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
