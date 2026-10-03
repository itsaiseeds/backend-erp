"""Stock writers racing each other: two requests for the same bags, packets or order.

Each race runs its contenders in real threads, released together by a barrier.
Every thread has its own database connection and sees only what the others
have *committed*, which is why this is a :class:`DMLTransactionTestCase` rather
than a ``TestCase`` -- inside one rolled-back transaction nothing could contend
for a lock at all.

What is asserted is the outcome, not the timing: with the locks in place
exactly one contender wins however the threads interleave.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from rest_framework import status
from rest_framework.test import APIClient

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import create_client_with_details
from aggregator.CustomOrderOperations import create_custom_order
from aggregator.models import (
    City,
    Country,
    CustomOrder,
    DispatchEntry,
    Order,
    Product,
    ProductPackaging,
    RawMaterialWaste,
    Stage,
    StageIds,
    State,
)
from aggregator.models.Status import StatusIds
from aggregator.OrderOperations import create_order, verify_order
from authentication.models import Admin, SalesPerson
from tests.common import DMLTransactionTestCase, book_raw_material_for_every_product

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
DISPATCH_URL = "/api/sales-admin/dispatch-order/{public_id}"

# How long a thread may take before the race is declared hung (a deadlock).
THREAD_TIMEOUT_SECONDS = 30


class StockConcurrencyTest(DMLTransactionTestCase):
    """Concurrent verify / dispatch / custom-order creation cannot oversell.

    tests/test_stock_concurrency.py::StockConcurrencyTest
    """

    def setUp(self):
        """Committed fixtures: one admin, one client, one bag, raw material for all."""
        super().setUp()
        superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        country = Country.objects.get(name="India")
        state = State.objects.get(name="Gujarat", country=country)
        self.city = City.objects.get(name="Surat", state=state)

        self.admin_user = User.objects.create_user(
            phone_number="9000000901",
            name="Race Admin",
            is_verified=True,
            created_by=superuser,
            verified_by=superuser,
        )
        Admin.objects.create(
            user=self.admin_user, created_by=superuser, can_update_stock_count=True
        )
        self.sales_person = User.objects.create_user(
            phone_number="9000000902",
            name="Race Sales",
            is_verified=True,
            created_by=superuser,
            verified_by=superuser,
        )
        SalesPerson.objects.create(
            user=self.sales_person, city=self.city, created_by=superuser
        )

        self.acme = create_client_with_details(
            company_name="Acme Seeds",
            company_phone="9876543210",
            gst_number="27AAPFU0939F1ZV",
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "line_2": "",
                    "pincode": "395007",
                    "city": self.city,
                    "state": state,
                    "country": country,
                    "label": "Warehouse",
                    "is_primary": True,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": "Acme Transport"}],
            actor=self.sales_person,
        )
        self.address = self.acme.client_addresses.first().address

        self.product = Product.objects.create(
            name="Alpha Seed",
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=superuser,
        )
        self.bag = ProductPackaging.objects.create(
            product=self.product,
            packet_weight=Decimal("1.000"),
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=superuser,
        )
        book_raw_material_for_every_product(actor=superuser)

    # -- helpers --------------------------------------------------------------

    def _race(self, *calls: Callable[[], object]) -> list[object]:
        """Run ``calls`` in parallel threads; return each result or raised exception."""
        barrier = threading.Barrier(len(calls))
        results: list[object] = [None] * len(calls)

        def run(index: int, call: Callable[[], object]) -> None:
            try:
                barrier.wait()
                results[index] = call()
            except Exception as exc:  # noqa: BLE001 -- the loser's error is the result
                results[index] = exc
            finally:
                connection.close()

        threads = [
            threading.Thread(target=run, args=(index, call))
            for index, call in enumerate(calls)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(THREAD_TIMEOUT_SECONDS)
            self.assertFalse(thread.is_alive(), "A contender hung -- likely a deadlock.")
        return results

    def _count_bags(self, bags: int) -> None:
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), bags),
            actor=self.admin_user,
        )

    def _book(self, quantity: int) -> Order:
        return create_order(
            client=self.acme,
            delivery_address=self.address,
            actor=self.sales_person,
            items=[{"product_packaging": self.bag, "quantity": quantity}],
        )

    # -- races ----------------------------------------------------------------

    def test_two_verifies_cannot_reserve_more_bags_than_exist(self):
        """5 bags counted, two orders of 3: only one may be confirmed.

        tests/test_stock_concurrency.py::StockConcurrencyTest::test_two_verifies_cannot_reserve_more_bags_than_exist
        """
        self._count_bags(5)
        first, second = self._book(3), self._book(3)

        results = self._race(
            lambda: verify_order(first, self.admin_user),
            lambda: verify_order(second, self.admin_user),
        )

        refusals = [r for r in results if isinstance(r, ValidationError)]
        self.assertEqual(len(refusals), 1, results)
        self.assertIn("Not enough stock to verify", str(refusals[0]))
        confirmed = Order.objects.filter(
            pk__in=[first.pk, second.pk], status_id=StatusIds.CONFIRMED
        )
        self.assertEqual(confirmed.count(), 1)
        self.assertEqual(inv.available_bags(self.bag), 2)

    def test_two_dispatches_of_one_order_record_one_journey(self):
        """The second dispatch is a clean 400, not a 500 and an orphan dispatch row.

        tests/test_stock_concurrency.py::StockConcurrencyTest::test_two_dispatches_of_one_order_record_one_journey
        """
        self._count_bags(5)
        order = self._book(2)
        verify_order(order, self.admin_user)
        body = {
            "from_city_id": self.city.id,
            "driver_name": "Ramesh Driver",
            "driver_number": "9876500002",
            "vehicle_number": "GJ05AB1234",
            "items": [
                {"product_packaging_public_id": self.bag.public_id, "lot_number": "LOT-1"}
            ],
        }

        def dispatch() -> int:
            client = APIClient()
            client.force_login(self.admin_user)
            url = DISPATCH_URL.format(public_id=order.public_id)
            return client.post(url, body, format="json").status_code

        results = self._race(dispatch, dispatch)

        self.assertEqual(
            sorted(results, key=str), [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )
        order.refresh_from_db()
        self.assertEqual(order.status.code, "DISPATCHED")
        self.assertEqual(DispatchEntry.objects.filter(order=order).count(), 1)

    def test_two_dispatches_at_once_get_different_challan_numbers(self):
        """The race the per-day advisory lock exists for.

        A challan number is the day's highest plus one, so two dispatches that
        read that maximum together would both pick it. There is no row to lock
        on the first dispatch of a day, so ``select_for_update`` cannot help --
        ``DispatchEntry._lock_challan_day`` serialises them instead.

        tests/test_stock_concurrency.py::StockConcurrencyTest::test_two_dispatches_at_once_get_different_challan_numbers
        """
        self._count_bags(10)
        first, second = self._book(2), self._book(2)
        for order in (first, second):
            verify_order(order, self.admin_user)
        body = {
            "from_city_id": self.city.id,
            "driver_name": "Ramesh Driver",
            "driver_number": "9876500002",
            "vehicle_number": "GJ05AB1234",
            "items": [
                {"product_packaging_public_id": self.bag.public_id, "lot_number": "LOT-1"}
            ],
        }

        def dispatch(order: Order) -> int:
            client = APIClient()
            client.force_login(self.admin_user)
            url = DISPATCH_URL.format(public_id=order.public_id)
            return client.post(url, body, format="json").status_code

        results = self._race(lambda: dispatch(first), lambda: dispatch(second))

        self.assertEqual(results, [status.HTTP_200_OK, status.HTTP_200_OK])
        numbers = sorted(
            DispatchEntry.objects.filter(order__in=[first, second]).values_list(
                "challan_number", flat=True
            )
        )
        self.assertEqual(len(set(numbers)), 2, numbers)
        # Consecutive, not merely distinct: the loser read the winner's number.
        self.assertEqual(
            [int(number.split("-")[1]) for number in numbers],
            [1, 2],
        )

    def test_two_custom_orders_cannot_spend_the_same_loose_packets(self):
        """5 loose packets counted, two custom orders of 3: only one is created.

        tests/test_stock_concurrency.py::StockConcurrencyTest::test_two_custom_orders_cannot_spend_the_same_loose_packets
        """
        pools = {
            (packaging.product, packaging.packet_weight)
            for packaging in ProductPackaging.objects.select_related("product")
        }
        inv.record_loose_stocks(counts=dict.fromkeys(pools, 5), actor=self.admin_user)

        def create() -> CustomOrder:
            return create_custom_order(
                client=self.acme,
                delivery_address=self.address,
                actor=self.admin_user,
                items=[
                    {
                        "product": self.product,
                        "packet_weight": self.bag.packet_weight,
                        "packets": 3,
                    }
                ],
            )

        results = self._race(create, create)

        refusals = [r for r in results if isinstance(r, ValidationError)]
        self.assertEqual(len(refusals), 1, results)
        self.assertIn("Not enough loose-packet stock", str(refusals[0]))
        self.assertEqual(CustomOrder.objects.filter(client=self.acme).count(), 1)
        self.assertEqual(
            inv.available_loose_packets(self.product, self.bag.packet_weight), 2
        )

    def test_a_write_waits_for_the_usability_switch_and_is_refused_once_it_commits(self):
        """The switch locks the product row; a racing write blocks, then sees it frozen.

        Thread A holds the row lock with ``is_usable = False`` uncommitted. Thread B's
        waste write must not slip through on the stale "usable" read: it waits for A to
        commit and is then refused.

        tests/test_stock_concurrency.py::StockConcurrencyTest::test_a_write_waits_for_the_usability_switch_and_is_refused_once_it_commits
        """
        locked, released = threading.Event(), threading.Event()
        outcome: dict[str, object] = {}

        def switch() -> None:
            try:
                with transaction.atomic():
                    Product.all_objects.select_for_update().get(pk=self.product.pk)
                    Product.objects.filter(pk=self.product.pk).update(is_usable=False)
                    locked.set()
                    released.wait(THREAD_TIMEOUT_SECONDS)
            finally:
                connection.close()

        def write() -> None:
            locked.wait(THREAD_TIMEOUT_SECONDS)
            try:
                outcome["result"] = inv.record_raw_waste(
                    product=self.product,
                    quantity_kg=Decimal("1"),
                    reason="",
                    actor=self.admin_user,
                )
            except Exception as exc:  # noqa: BLE001 -- the refusal is the result
                outcome["result"] = exc
            finally:
                connection.close()

        switcher = threading.Thread(target=switch)
        writer = threading.Thread(target=write)
        switcher.start()
        writer.start()
        self.assertTrue(locked.wait(THREAD_TIMEOUT_SECONDS))
        writer.join(1.0)
        self.assertTrue(writer.is_alive(), "The write should be blocked on the product lock.")

        released.set()
        switcher.join(THREAD_TIMEOUT_SECONDS)
        writer.join(THREAD_TIMEOUT_SECONDS)
        self.assertFalse(switcher.is_alive() or writer.is_alive(), "A contender hung.")

        self.assertIsInstance(outcome["result"], ValidationError)
        self.assertIn("not usable", str(outcome["result"]))
        self.assertEqual(RawMaterialWaste.objects.filter(product=self.product).count(), 0)
