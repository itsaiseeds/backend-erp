"""``GET /api/sales-admin/product-stock-ledger/<public_id>`` and the ledger commands.

Run: bash scripts/run.sh test-serial tests/test_stock_ledger_api.py
"""

from __future__ import annotations

import datetime
import gzip
import json
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework import serializers, status

from aggregator import InventoryOperations as inv
from aggregator import StockLedgerOperations
from aggregator.models import Product, StockEvent, StockEventLine
from aggregator.StockLedgerReport import product_ledger_rows
from api.export_views import MAX_EXPORT_RANGE_DAYS
from api.sales_admin.ProductStockLedgerView import ProductStockLedgerSerializer
from authentication.models import Admin, User
from tests.common import WebApiTestCase
from tests.stock_ledger_support import TODAY, LedgerWorldTestCase

URL = "/api/sales-admin/product-stock-ledger/{}"


def documented_keys_mismatches(serializer, data, path="") -> list[str]:
    """Where ``data`` and the documenting ``serializer`` disagree on keys, recursively."""
    if isinstance(serializer, serializers.ListSerializer):
        problems = []
        for index, item in enumerate(data):
            problems += documented_keys_mismatches(serializer.child, item, f"{path}[{index}]")
        return problems
    if not isinstance(serializer, serializers.Serializer) or data is None:
        return []
    fields = serializer.fields
    problems = []
    if set(data) - set(fields):
        problems.append(f"{path}: undocumented {sorted(set(data) - set(fields))}")
    if set(fields) - set(data):
        problems.append(f"{path}: missing {sorted(set(fields) - set(data))}")
    for name, field in fields.items():
        if name in data:
            problems += documented_keys_mismatches(field, data[name], f"{path}.{name}")
    return problems


class StockLedgerApiTest(LedgerWorldTestCase, WebApiTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.app_admin = User.objects.create_user(
            "9520000001", "Ledger Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        Admin.objects.create(user=cls.app_admin, created_by=cls.su, can_update_stock_count=True)

    def setUp(self):
        super().setUp()
        self.login_as(self.app_admin)

    def _get(self, product=None, **params):
        product = product or self.product
        params.setdefault("start_date", TODAY.isoformat())
        params.setdefault("end_date", TODAY.isoformat())
        return self.client.get(URL.format(product.public_id), params)

    def _go_live_with_some_history(self):
        StockLedgerOperations.seed_ledger()
        self.raw(self.product, "100000")
        self.raw(self.other_product, "100000")
        self.pouches("1000")
        self.count_everything({self.pp1: 10, self.qq1: 5})

    # -- validation ------------------------------------------------------------------

    def test_a_ledger_that_has_not_started_is_a_400(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_a_ledger_that_has_not_started_is_a_400"""
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_bad_requests_are_400s_and_unknown_products_404(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_bad_requests_are_400s_and_unknown_products_404"""
        self._go_live_with_some_history()
        before_live = (TODAY - datetime.timedelta(days=1)).isoformat()
        cases = [
            ("before go-live", {"start_date": before_live}, 400),
            (
                f"range over the {MAX_EXPORT_RANGE_DAYS}-day cap",
                {"end_date": (TODAY + datetime.timedelta(days=MAX_EXPORT_RANGE_DAYS)).isoformat()},
                400,
            ),
            ("end before start", {"start_date": TODAY.isoformat(), "end_date": before_live}, 400),
            ("unparseable date", {"start_date": "not-a-date"}, 400),
            ("missing dates", {"start_date": "", "end_date": ""}, 400),
            ("page size over the cap", {"page_size": 500}, 400),
        ]
        for label, params, expected in cases:
            with self.subTest(case=label):
                self.assertEqual(self._get(**params).status_code, expected)

        with self.subTest(case="unknown product"):
            response = self.client.get(
                URL.format("P-DOESNOTEXIST"),
                {"start_date": TODAY.isoformat(), "end_date": TODAY.isoformat()},
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        with self.subTest(case="deleted product"):
            Product.all_objects.filter(pk=self.other_product.pk).update(is_deleted=True)
            self.assertEqual(
                self._get(self.other_product).status_code, status.HTTP_404_NOT_FOUND
            )

    def test_the_go_live_message_names_the_start_date(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_the_go_live_message_names_the_start_date"""
        self._go_live_with_some_history()
        response = self._get(start_date=(TODAY - datetime.timedelta(days=3)).isoformat())
        self.assertIn(f"Stock ledger starts on {TODAY.isoformat()}", str(response.data))

    # -- the response ------------------------------------------------------------------

    def test_the_response_matches_its_documented_serializer(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_the_response_matches_its_documented_serializer"""
        self._go_live_with_some_history()
        response = self._get()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(
            documented_keys_mismatches(ProductStockLedgerSerializer(), response.data), []
        )
        body = response.data
        self.assertEqual(body["product"]["public_id"], self.product.public_id)
        self.assertEqual(body["results"][0]["event"], "OPENING_BALANCE")
        self.assertEqual(body["results"][-1]["event"], "CLOSING_BALANCE")
        self.assertEqual(body["count"], len(body["results"]))

    def test_opening_and_closing_sit_on_the_first_and_last_pages(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_opening_and_closing_sit_on_the_first_and_last_pages"""
        self._go_live_with_some_history()
        for _ in range(3):
            self.count_bags({self.pp1: 11}), self.count_bags({self.pp1: 10})
        total = self._get().data["count"]
        self.assertGreater(total, 4)

        pages = []
        page = 1
        while True:
            response = self._get(page=page, page_size=3)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
            pages.append(response.data["results"])
            if page * 3 >= total:
                break
            page += 1
        flat = [row for rows in pages for row in rows]
        self.assertEqual(len(flat), total)
        self.assertEqual(flat[0]["event"], "OPENING_BALANCE")
        self.assertEqual(pages[0][0]["event"], "OPENING_BALANCE")
        self.assertEqual(flat[-1]["event"], "CLOSING_BALANCE")
        self.assertEqual(pages[-1][-1]["event"], "CLOSING_BALANCE")
        self.assertEqual(
            [row["event"] for row in flat].count("OPENING_BALANCE"), 1, "only on page one"
        )

    def test_rows_reconcile_per_configuration_and_other_products_lots_are_not_listed(self):
        """Each configuration reconciles alone: incoming - packed = available.

        tests/test_stock_ledger_api.py::StockLedgerApiTest::test_rows_reconcile_and_a_shared_material_shows_the_other_products_use
        """
        self._go_live_with_some_history()
        self.pouches("500", recipe=self.recipe_q)  # booked against Q's recipe
        self.count_bags({self.pp1: 12})
        self.count_bags({self.qq1: 8})

        rows = self._get().data["results"]
        inward_rows = [
            row for row in rows if row["source"] and row["source"]["kind"] == "inward_other_material"
        ]
        self.assertEqual(len(inward_rows), 1, "Q's lots are not listed in P's report")
        self.assertNotIn("Ledger Q", inward_rows[0]["source"]["label"])

        for row in rows:
            for material in row["other_materials"]:
                with self.subTest(event=row["event"], at=row["occurred_at"]):
                    self.assertEqual(material["packet_weight"], "1.000")
                    self.assertEqual(
                        Decimal(material["incoming"]) - Decimal(material["packed"]),
                        Decimal(material["available"]),
                    )
        closing = rows[-1]["other_materials"][0]
        # P packed 12 bags x 20 = 240 at 1 a packet; Q's 160 is not in P's pool.
        self.assertEqual(closing["packed"], "240.000")
        self.assertNotIn("used_by_other_products", closing)
        self.assertEqual(
            closing["available"], str(Decimal(closing["incoming"]) - 240)
        )

    def test_only_this_endpoint_is_gzipped_and_only_when_asked(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_only_this_endpoint_is_gzipped_and_only_when_asked"""
        self._go_live_with_some_history()
        params = {"start_date": TODAY.isoformat(), "end_date": TODAY.isoformat()}
        url = URL.format(self.product.public_id)

        plain = self.client.get(url, params)
        zipped = self.client.get(url, params, HTTP_ACCEPT_ENCODING="gzip")

        self.assertNotIn("Content-Encoding", plain)
        self.assertEqual(zipped["Content-Encoding"], "gzip")
        self.assertIn("Accept-Encoding", zipped["Vary"])
        self.assertLess(len(zipped.content), len(plain.content) / 3)
        self.assertEqual(json.loads(gzip.decompress(zipped.content)), json.loads(plain.content))
        other = self.client.get("/api/sales-admin/bag-stock", HTTP_ACCEPT_ENCODING="gzip")
        self.assertNotIn("Content-Encoding", other, "no other endpoint is compressed")

    # -- caching and the daily allowance -------------------------------------------

    def _tomorrow_window(self, days):
        end = TODAY + datetime.timedelta(days=days)
        return {"start_date": TODAY.isoformat(), "end_date": end.isoformat()}

    def test_a_window_is_built_once_and_every_page_and_repeat_is_served_from_cache(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_a_window_is_built_once_and_every_page_and_repeat_is_served_from_cache"""
        self._go_live_with_some_history()
        with mock.patch(
            "api.sales_admin.ProductStockLedgerView.product_ledger_rows",
            wraps=product_ledger_rows,
        ) as build:
            first = self._get(page=1, page_size=3)
            second = self._get(page=2, page_size=3)
            repeat = self._get(page=1, page_size=3)
            self.assertEqual(build.call_count, 1)
        self.assertEqual(first.data, repeat.data)
        self.assertNotEqual(first.data["results"], second.data["results"])
        self.assertRegex(first["Cache-Control"], r"^private, max-age=\d+$")
        self.assertLessEqual(int(first["Cache-Control"].split("=")[1]), 300)

    def test_a_third_new_window_for_one_product_is_refused_but_cached_ones_are_not(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_a_third_new_window_for_one_product_is_refused_but_cached_ones_are_not"""
        self._go_live_with_some_history()
        for days in (0, 1):
            self.assertEqual(self._get(**self._tomorrow_window(days)).status_code, 200)

        refused = self._get(**self._tomorrow_window(2))
        self.assertEqual(refused.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("limit", str(refused.data).lower())
        self.assertGreater(int(refused["Retry-After"]), 0)

        # Already-built windows stay free, however often they are asked for.
        for _ in range(3):
            self.assertEqual(self._get(**self._tomorrow_window(1)).status_code, 200)

    def test_the_allowance_is_per_user_and_per_product(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_the_allowance_is_per_user_and_per_product"""
        self._go_live_with_some_history()
        for days in (0, 1):
            self._get(**self._tomorrow_window(days))
        self.assertEqual(
            self._get(**self._tomorrow_window(2)).status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )

        # Another product is untouched ...
        self.assertEqual(
            self._get(self.other_product, **self._tomorrow_window(2)).status_code, 200
        )
        # ... and so is another admin on the same product.
        other = User.objects.create_user(
            "9520000002", "Second Admin", created_by=self.su, verified_by=self.su, is_verified=True
        )
        Admin.objects.create(user=other, created_by=self.su, can_update_stock_count=True)
        self.client.logout()
        self.login_as(other)
        self.assertEqual(self._get(**self._tomorrow_window(2)).status_code, 200)

    def test_a_refused_or_failed_request_does_not_use_the_allowance(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_a_refused_or_failed_request_does_not_use_the_allowance"""
        self._go_live_with_some_history()
        before_live = (TODAY - datetime.timedelta(days=1)).isoformat()
        for _ in range(4):
            self.assertEqual(self._get(start_date=before_live).status_code, 400)
        for days in (0, 1):
            self.assertEqual(self._get(**self._tomorrow_window(days)).status_code, 200)

    def test_the_closing_row_matches_the_live_screens(self):
        """tests/test_stock_ledger_api.py::StockLedgerApiTest::test_the_closing_row_matches_the_live_screens"""
        self._go_live_with_some_history()
        order = self.order(self.pp1, 3)
        self.dispatch(order, self.pp1)
        inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("12"), reason="x", actor=self.su
        )
        closing = self._get().data["results"][-1]
        bag = closing["bag_pools"][0]
        self.assertEqual(bag["on_hand"], inv.on_hand_bags(self.pp1))
        self.assertEqual(bag["reserved"], inv.reserved_bags(self.pp1))
        self.assertEqual(bag["consumed"], inv.consumed_bags(self.pp1))
        self.assertEqual(bag["available"], inv.available_bags(self.pp1))
        raw = closing["raw_material"]
        self.assertEqual(Decimal(raw["available"]), inv.raw_available_kg(self.product))
        self.assertEqual(Decimal(raw["incoming"]), inv.raw_inward_kg(self.product))
        self.assertEqual(Decimal(raw["wasted"]), inv.raw_wasted_kg(self.product))


class StockLedgerCommandsTest(LedgerWorldTestCase):
    # The check command is the thing under test here, so the guard stays off.
    stock_ledger_guard = False

    def setUp(self):
        super().setUp()
        self.raw(self.product, "5000")
        self.pouches("1000")
        self.count_everything({self.pp1: 10})
        # Booked before go-live, so these events pre-date the seed.
        StockEventLine.objects.all().delete()
        StockEvent.objects.all().delete()

    def test_seed_writes_the_live_position_once_and_moves_nothing(self):
        """tests/test_stock_ledger_api.py::StockLedgerCommandsTest::test_seed_writes_the_live_position_once_and_moves_nothing"""
        live = StockLedgerOperations.read_positions([self.product.pk])
        out = StringIO()
        call_command("seed_stock_ledger", stdout=out)
        self.assertIn("Seeded the stock ledger", out.getvalue())
        self.assertEqual(StockLedgerOperations.read_positions([self.product.pk]), live)
        self.assertEqual(StockLedgerOperations.check_ledger(), [])
        self.assertTrue(
            StockEvent.objects.filter(product=self.product, event_type=1).count() == 1
        )
        with self.assertRaises(CommandError):
            call_command("seed_stock_ledger", stdout=StringIO())

    def test_check_exits_zero_when_in_sync_and_nonzero_after_a_tampered_line(self):
        """tests/test_stock_ledger_api.py::StockLedgerCommandsTest::test_check_exits_zero_when_in_sync_and_nonzero_after_a_tampered_line"""
        call_command("seed_stock_ledger", stdout=StringIO())
        call_command("check_stock_ledger", stdout=StringIO())

        line = StockEventLine.objects.filter(
            event__product=self.product, d_on_hand__isnull=False
        ).first()
        line.d_on_hand += 1
        line.save()
        with self.assertRaises(CommandError):
            call_command("check_stock_ledger", stdout=StringIO(), stderr=StringIO())


class StockLedgerAdminTest(LedgerWorldTestCase, WebApiTestCase):
    """The ledger is visible in the Django admin, and read-only even for a superuser."""

    def setUp(self):
        super().setUp()
        self.raw(self.product, "1000")
        # 5 bags x 20 packets x 1 leaflet: the count is refused without them.
        self.pouches("100")
        self.count_everything({self.pp1: 5})
        self.event = StockEvent.objects.filter(product=self.product).first()
        self.login_as(self.su)

    def test_the_changelist_and_detail_render_with_the_lines_inline(self):
        """tests/test_stock_ledger_api.py::StockLedgerAdminTest::test_the_changelist_and_detail_render_with_the_lines_inline"""
        listing = self.client.get("/admin/aggregator/stockevent/")
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, "PACKED")

        detail = self.client.get(f"/admin/aggregator/stockevent/{self.event.pk}/change/")
        self.assertEqual(detail.status_code, 200)

        self.assertEqual(self.client.get("/admin/aggregator/packedrecipelayer/").status_code, 200)

    def test_nobody_can_add_change_or_delete_a_ledger_row(self):
        """tests/test_stock_ledger_api.py::StockLedgerAdminTest::test_nobody_can_add_change_or_delete_a_ledger_row"""
        base = "/admin/aggregator/stockevent/"
        self.assertEqual(self.client.get(base + "add/").status_code, 403)
        self.assertEqual(self.client.post(base + f"{self.event.pk}/change/", {}).status_code, 403)
        self.assertEqual(self.client.get(base + f"{self.event.pk}/delete/").status_code, 403)
        self.assertTrue(StockEvent.objects.filter(pk=self.event.pk).exists())
