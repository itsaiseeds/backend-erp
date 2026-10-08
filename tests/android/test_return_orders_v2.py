"""Android API v2: many returns per order (docs/prd/multiple-return-orders.md).

tests/android/test_return_orders_v2.py
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator.models import ReturnOrder
from api.return_order_serializers import (
    ReturnOrderPrefillSerializer,
    ReturnOrderPrefillV2Serializer,
)
from tests.test_return_orders import ReturnWorldTestCase
from tests.test_stock_ledger_api import documented_keys_mismatches

V1 = "/android/api/v1/"
V2 = "/android/api/v2/"
ADMIN = "/api/sales-admin/"


class ReturnOrdersV2ApiTest(ReturnWorldTestCase):
    """tests/android/test_return_orders_v2.py::ReturnOrdersV2ApiTest"""

    def setUp(self):
        super().setUp()
        self.droid = APIClient()
        token, _ = Token.objects.get_or_create(user=self.sp_user)
        self.droid.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.web = APIClient()
        self.web.force_login(self.admin_user)

    def body(self, packets):
        return {
            "items": [
                {
                    "product_public_id": self.product.public_id,
                    "packet_weight": "1.000",
                    "packets": packets,
                    "price_per_packet": "2.00",
                }
            ]
        }

    def post(self, version, order, packets):
        return self.droid.post(
            f"{version}return-order/{order.public_id}", self.body(packets), format="json"
        )

    def test_v2_get_lists_every_live_return_newest_first(self):
        """tests/android/test_return_orders_v2.py::ReturnOrdersV2ApiTest::test_v2_get_lists_every_live_return_newest_first"""
        order = self.dispatched_order()  # 40 packets
        url = f"{V2}return-order/{order.public_id}"
        empty = self.droid.get(url)
        self.assertEqual(empty.status_code, status.HTTP_200_OK, empty.content)
        self.assertEqual(empty.data["return_orders"], [])
        self.assertNotIn("return_order", empty.data)

        first = self.post(V2, order, 10).data["public_id"]
        second = self.post(V2, order, 15).data["public_id"]
        rejected = self.post(V2, order, 5).data["public_id"]
        self.web.post(f"{ADMIN}reject-return-order/{rejected}")

        got = self.droid.get(url)
        self.assertEqual(documented_keys_mismatches(ReturnOrderPrefillV2Serializer(), got.data), [])
        self.assertEqual([r["public_id"] for r in got.data["return_orders"]], [second, first])
        self.assertEqual(got.data["lines"][0]["returnable_packets"], 15)

    def test_v2_post_allows_a_second_return_within_the_sum(self):
        """tests/android/test_return_orders_v2.py::ReturnOrdersV2ApiTest::test_v2_post_allows_a_second_return_within_the_sum"""
        order = self.dispatched_order()
        one, two = self.post(V2, order, 30), self.post(V2, order, 10)
        self.assertEqual(one.status_code, status.HTTP_201_CREATED, one.content)
        self.assertEqual(two.status_code, status.HTTP_201_CREATED, two.content)
        self.assertNotEqual(one.data["public_id"], two.data["public_id"])
        self.assertTrue(two.data["public_id"].startswith("RET-"))

        over = self.post(V2, order, 1)  # 30 + 10 + 1 > 40
        self.assertEqual(over.status_code, status.HTTP_400_BAD_REQUEST, over.content)
        self.assertEqual(ReturnOrder.objects.filter(order=order).count(), 2)

    def test_v1_keeps_the_one_live_return_rule_and_single_return_order(self):
        """tests/android/test_return_orders_v2.py::ReturnOrdersV2ApiTest::test_v1_keeps_the_one_live_return_rule_and_single_return_order"""
        order = self.dispatched_order()
        url = f"{V1}return-order/{order.public_id}"
        self.assertIsNone(self.droid.get(url).data["return_order"])

        older = self.post(V1, order, 10)
        self.assertEqual(older.status_code, status.HTTP_201_CREATED, older.content)
        self.assertEqual(self.post(V1, order, 5).status_code, status.HTTP_400_BAD_REQUEST)

        # A v2 return can still be added; v1 GET then shows the newest one only.
        newer = self.post(V2, order, 5).data["public_id"]
        got = self.droid.get(url)
        self.assertEqual(documented_keys_mismatches(ReturnOrderPrefillSerializer(), got.data), [])
        self.assertEqual(got.data["return_order"]["public_id"], newer)
        self.assertNotIn("return_orders", got.data)
        # ...and v1 still refuses while any live return exists.
        self.assertEqual(self.post(V1, order, 1).status_code, status.HTTP_400_BAD_REQUEST)

    def test_inherited_v1_endpoints_are_served_under_v2(self):
        """tests/android/test_return_orders_v2.py::ReturnOrdersV2ApiTest::test_inherited_v1_endpoints_are_served_under_v2"""
        order = self.dispatched_order()
        self.post(V2, order, 5)
        listing = self.droid.get(f"{V2}get-return-orders", {"order": order.public_id})
        self.assertEqual(listing.status_code, status.HTTP_200_OK, listing.content)

    def test_admin_order_detail_lists_all_live_returns_and_the_deprecated_key(self):
        """tests/android/test_return_orders_v2.py::ReturnOrdersV2ApiTest::test_admin_order_detail_lists_all_live_returns_and_the_deprecated_key"""
        order = self.dispatched_order()
        first = self.post(V2, order, 10).data["public_id"]
        second = self.post(V2, order, 10).data["public_id"]
        detail = self.web.get(f"{ADMIN}order/{order.public_id}")
        self.assertEqual([r["public_id"] for r in detail.data["return_orders"]], [second, first])
        self.assertEqual(detail.data["return_order"]["public_id"], second)

    def test_admin_verbs_accept_a_second_live_return_within_the_limit(self):
        """tests/android/test_return_orders_v2.py::ReturnOrdersV2ApiTest::test_admin_verbs_accept_a_second_live_return_within_the_limit"""
        order = self.dispatched_order()
        first = self.post(V2, order, 20).data["public_id"]
        second = self.post(V2, order, 20).data["public_id"]
        accept = {"include_in_other_raw_materials": False}
        for public_id in (first, second):
            response = self.web.post(
                f"{ADMIN}accept-return-order/{public_id}", accept, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        edited = self.web.patch(f"{ADMIN}edit-return-order/{first}", self.body(1), format="json")
        self.assertEqual(edited.status_code, status.HTTP_400_BAD_REQUEST, "accepted: not editable")
