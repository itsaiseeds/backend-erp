"""The five date-range exports under ``/api/sales-admin/export/``.

What is proven here is what each export *returns*: the window it honours, the
rows it leaves out, and the shape it groups them into. Authentication and role
gating are proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers, status

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import create_client_with_details
from aggregator.CustomOrderOperations import create_custom_order
from aggregator.models import (
    City,
    Country,
    InwardOtherMaterial,
    InwardRawMaterial,
    OtherMaterialRecipe,
    OtherMaterialType,
    Party,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
)
from aggregator.OrderOperations import create_order
from api.sales_admin.ExportCustomOrdersView import ExportCustomOrdersResponseSerializer
from api.sales_admin.ExportDispatchReceiptsView import ExportDispatchReceiptsResponseSerializer
from api.sales_admin.ExportInventorySnapshotsView import (
    ExportInventorySnapshotsResponseSerializer,
)
from api.sales_admin.ExportInwardEntriesView import ExportInwardEntriesResponseSerializer
from api.sales_admin.ExportOrdersView import ExportOrdersResponseSerializer
from authentication.models import Admin, SalesPerson
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
ORDERS_URL = "/api/sales-admin/export/orders"
CUSTOM_ORDERS_URL = "/api/sales-admin/export/custom-orders"
DISPATCH_RECEIPTS_URL = "/api/sales-admin/export/dispatch-receipts"
INWARD_URL = "/api/sales-admin/export/inward-entries"
SNAPSHOTS_URL = "/api/sales-admin/export/inventory-snapshots"
VERIFY_URL = "/api/sales-admin/verify-order/{public_id}"
DISPATCH_URL = "/api/sales-admin/dispatch-order/{public_id}"

AUDIT_KEYS = {"created_by", "is_deleted", "deleted_at", "deleted_by", "updated_at"}


def _keys(value) -> set[str]:
    """Every dict key anywhere inside ``value``."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in _keys(v)}
    return set()


def _documented_keys_mismatches(serializer, data, path="") -> list[str]:
    """Where ``data`` and the documenting ``serializer`` disagree on keys, recursively.

    The export schemas are hand-written serializers, so this keeps the OpenAPI doc
    honest: every key a response carries is documented, and every documented key
    is really there, at every level of nesting.
    """
    if isinstance(serializer, serializers.ListSerializer):
        problems = []
        for index, item in enumerate(data):
            problems += _documented_keys_mismatches(serializer.child, item, f"{path}[{index}]")
        return problems
    if not isinstance(serializer, serializers.Serializer) or data is None:
        return []
    fields = serializer.fields
    problems = [f"{path}: undocumented {sorted(set(data) - set(fields))}"] if set(data) - set(fields) else []
    if set(fields) - set(data):
        problems.append(f"{path}: missing {sorted(set(fields) - set(data))}")
    for name, field in fields.items():
        if name in data:
            problems += _documented_keys_mismatches(field, data[name], f"{path}.{name}")
    return problems


def _ist(day, at=time.min) -> datetime:
    return timezone.make_aware(datetime.combine(day, at))


class ExportApiTest(WebApiTestCase):
    """tests/test_export_api.py::ExportApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        country = Country.objects.get(name="India")
        state = State.objects.get(name="Gujarat", country=country)
        cls.city = City.objects.get(name="Surat", state=state)

        cls.admin_user = User.objects.create_user(
            phone_number="9000000801",
            name="Export Admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=cls.admin_user, created_by=cls.superuser, can_update_stock_count=True
        )
        cls.sales_person = User.objects.create_user(
            phone_number="9000000802",
            name="Export Sales",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(user=cls.sales_person, city=cls.city, created_by=cls.superuser)

        cls.client_row = create_client_with_details(
            company_name="Acme Seeds",
            company_phone="9876543210",
            gst_number="27AAPFU0939F1ZV",
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "line_2": "",
                    "pincode": "395007",
                    "city": cls.city,
                    "state": state,
                    "country": country,
                    "label": "Warehouse",
                    "is_primary": True,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": "Acme Transport"}],
            actor=cls.sales_person,
        )
        cls.address = cls.client_row.client_addresses.first().address

        cls.product = Product.objects.create(
            name="Alpha Seed",
            crop_id=1,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )
        cls.bag = ProductPackaging.objects.create(
            product=cls.product,
            packet_weight=Decimal("1.000"),
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=cls.superuser,
        )
        cls.party = Party.objects.create(name="ABC Traders", city_id=1, created_by=cls.admin_user)
        cls.today = inv.today()

    def setUp(self):
        super().setUp()
        self.login_as(self.admin_user)

    # -- helpers --------------------------------------------------------------

    def _export(self, url, start, end=None):
        end = end or start
        return self.client.get(
            url, {"start_date": start.isoformat(), "end_date": end.isoformat()}
        )

    def _order(self, **kwargs):
        return create_order(
            client=self.client_row,
            delivery_address=self.address,
            actor=self.sales_person,
            items=[{"product_packaging": self.bag, "quantity": 2}],
            **kwargs,
        )

    def _backdate(self, row, when):
        type(row).all_objects.filter(id=row.id).update(created_at=when)

    def _dispatch(self, order):
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), 400), actor=self.admin_user
        )
        self.client.post(VERIFY_URL.format(public_id=order.public_id), {}, format="json")
        self.client.post(
            DISPATCH_URL.format(public_id=order.public_id),
            {
                "from_city_id": self.city.id,
                "driver_name": "Ramesh Driver",
                "driver_number": "9876500002",
                "vehicle_number": "GJ05AB1234",
                "items": [
                    {"product_packaging_public_id": self.bag.public_id, "lot_number": "LOT-1"}
                ],
            },
            format="json",
        )

    # -- the shared window ----------------------------------------------------

    def test_the_window_is_validated(self):
        """tests/test_export_api.py::ExportApiTest::test_the_window_is_validated"""
        start = self.today - timedelta(days=30)
        cases = {
            "missing": {},
            "end before start": {
                "start_date": self.today.isoformat(),
                "end_date": (self.today - timedelta(days=1)).isoformat(),
            },
            "32 days": {
                "start_date": (start - timedelta(days=1)).isoformat(),
                "end_date": self.today.isoformat(),
            },
        }
        for label, params in cases.items():
            with self.subTest(case=label):
                resp = self.client.get(ORDERS_URL, params)
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.data)

        resp = self._export(ORDERS_URL, start, self.today)  # exactly 31 days
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def test_the_window_is_inclusive_ist_days(self):
        """First and last instant of the window's IST days are in; a moment either side is out.

        tests/test_export_api.py::ExportApiTest::test_the_window_is_inclusive_ist_days
        """
        start, end = self.today - timedelta(days=5), self.today - timedelta(days=4)
        inside = {
            self._order(): _ist(start),
            self._order(): _ist(end, time.max),
        }
        outside = {
            self._order(): _ist(start) - timedelta(microseconds=1),
            self._order(): _ist(end + timedelta(days=1)),
        }
        for order, when in {**inside, **outside}.items():
            self._backdate(order, when)

        resp = self._export(ORDERS_URL, start, end)

        self.assertEqual(
            {row["public_id"] for row in resp.data["results"]},
            {order.public_id for order in inside},
        )
        self.assertEqual(resp.data["count"], 2)

    # -- orders ---------------------------------------------------------------

    def test_orders_export_nests_items_names_the_order_city_and_skips_deleted(self):
        """tests/test_export_api.py::ExportApiTest::test_orders_export_nests_items_names_the_order_city_and_skips_deleted"""
        live = self._order()
        deleted = self._order()
        deleted.mark_deleted(self.admin_user)

        resp = self._export(ORDERS_URL, self.today)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual([row["public_id"] for row in resp.data["results"]], [live.public_id])
        row = resp.data["results"][0]
        self.assertEqual(row["client"]["company_name"], "Acme Seeds")
        self.assertEqual(row["city"], {"id": self.city.id, "name": "Surat"})
        self.assertEqual(len(row["items"]), 1)
        self.assertEqual(row["items"][0]["packaging"]["public_id"], self.bag.public_id)
        self.assertEqual(row["items"][0]["quantity"], 2)
        self.assertEqual(row["total_amount"], "2000.00")
        self.assertFalse(_keys(resp.data) & AUDIT_KEYS)
        self.assertEqual(_documented_keys_mismatches(ExportOrdersResponseSerializer(), resp.data), [])

    # -- custom orders --------------------------------------------------------

    def test_custom_orders_export_nests_items_and_names_the_order_city(self):
        """tests/test_export_api.py::ExportApiTest::test_custom_orders_export_nests_items_and_names_the_order_city"""
        weight = Decimal("1.000")
        inv.record_loose_stocks(counts={(self.product, weight): 50}, actor=self.admin_user)
        order = create_custom_order(
            client=self.client_row,
            delivery_address=self.address,
            actor=self.admin_user,
            items=[{"product": self.product, "packet_weight": weight, "packets": 5}],
        )
        old = create_custom_order(
            client=self.client_row,
            delivery_address=self.address,
            actor=self.admin_user,
            items=[{"product": self.product, "packet_weight": weight, "packets": 1}],
        )
        self._backdate(old, _ist(self.today - timedelta(days=2)))

        resp = self._export(CUSTOM_ORDERS_URL, self.today)

        self.assertEqual([row["public_id"] for row in resp.data["results"]], [order.public_id])
        row = resp.data["results"][0]
        self.assertEqual(row["city"]["name"], "Surat")
        self.assertEqual(row["items"][0]["product"]["public_id"], self.product.public_id)
        self.assertEqual(row["items"][0]["packets"], 5)
        self.assertFalse(_keys(resp.data) & AUDIT_KEYS)
        self.assertEqual(_documented_keys_mismatches(ExportCustomOrdersResponseSerializer(), resp.data), [])

    # -- dispatch receipts ----------------------------------------------------

    def test_dispatch_receipts_export_only_complete_challans(self):
        """A private dispatch is complete; an agency dispatch awaiting its LR is not.

        tests/test_export_api.py::ExportApiTest::test_dispatch_receipts_export_only_complete_challans
        """
        agency = self.client_row.client_transport_agencies.first().transport_agency
        private = self._order()
        awaiting_lr = self._order(transport_agency=agency)
        self._order()  # booked but never dispatched: no challan
        self._dispatch(private)
        self._dispatch(awaiting_lr)

        resp = self._export(DISPATCH_RECEIPTS_URL, self.today)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(
            [row["order_public_id"] for row in resp.data["results"]], [private.public_id]
        )
        row = resp.data["results"][0]
        self.assertEqual(row["city"]["name"], "Surat")
        self.assertEqual(row["receiver_details"]["company_name"], "Acme Seeds")
        self.assertEqual(row["items"][0]["lot_number"], "LOT-1")
        self.assertFalse(_keys(resp.data) & AUDIT_KEYS)
        self.assertEqual(_documented_keys_mismatches(ExportDispatchReceiptsResponseSerializer(), resp.data), [])

    # -- inward entries -------------------------------------------------------

    def test_inward_export_groups_raw_and_other_entries_by_booking_day(self):
        """tests/test_export_api.py::ExportApiTest::test_inward_export_groups_raw_and_other_entries_by_booking_day"""
        yesterday = self.today - timedelta(days=1)
        recipe = OtherMaterialRecipe.objects.create(
            product=Product.objects.get(name="SAI-33"),
            material_type=OtherMaterialType.objects.get(name="packet_outer_cover"),
            packet_weight=Decimal("2.500"),
            quantity=Decimal("3.000"),
            created_by=self.admin_user,
        )
        raw_old = InwardRawMaterial.objects.create(
            product=self.product,
            party=self.party,
            quantity_kg=Decimal("100.000"),
            created_by=self.admin_user,
        )
        self._backdate(raw_old, _ist(yesterday, time(10)))
        raw_new = InwardRawMaterial.objects.create(
            product=self.product,
            party=self.party,
            quantity_kg=Decimal("50.000"),
            created_by=self.admin_user,
        )
        other_new = InwardOtherMaterial.objects.create(
            recipe=recipe,
            party=self.party,
            quantity=Decimal("20.000"),
            effective_date=self.today,
            created_by=self.admin_user,
        )

        resp = self._export(INWARD_URL, yesterday, self.today)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        days = resp.data["results"]
        self.assertEqual([day["date"] for day in days], [yesterday.isoformat(), self.today.isoformat()])
        self.assertEqual([r["public_id"] for r in days[0]["raw_materials"]], [raw_old.public_id])
        self.assertEqual(days[0]["other_materials"], [])
        self.assertEqual([r["public_id"] for r in days[1]["raw_materials"]], [raw_new.public_id])
        self.assertEqual([r["public_id"] for r in days[1]["other_materials"]], [other_new.public_id])
        self.assertFalse(_keys(resp.data) & AUDIT_KEYS)
        self.assertEqual(_documented_keys_mismatches(ExportInwardEntriesResponseSerializer(), resp.data), [])

    # -- inventory snapshots --------------------------------------------------

    def test_snapshot_export_returns_every_counted_day_grouped_by_date(self):
        """History is kept, so several days come back -- counted figures only.

        tests/test_export_api.py::ExportApiTest::test_snapshot_export_returns_every_counted_day_grouped_by_date
        """
        yesterday = self.today - timedelta(days=1)
        weight = Decimal("1.000")
        for day, bags, packets in ((yesterday, 100, 30), (self.today, 90, 25)):
            inv.record_stock_count(
                product_packaging=self.bag, bags=bags, actor=self.admin_user, snapshot_date=day
            )
            inv.record_loose_stock(
                product=self.product,
                packet_weight=weight,
                packets=packets,
                actor=self.admin_user,
                snapshot_date=day,
            )

        resp = self._export(SNAPSHOTS_URL, yesterday, self.today)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        days = resp.data["results"]
        self.assertEqual(
            [day["snapshot_date"] for day in days], [yesterday.isoformat(), self.today.isoformat()]
        )
        self.assertEqual([b["bags"] for b in days[0]["bag_snapshots"]], [100])
        self.assertEqual([b["bags"] for b in days[1]["bag_snapshots"]], [90])
        self.assertEqual([loose["packets"] for loose in days[0]["loose_snapshots"]], [30])
        self.assertEqual([loose["packets"] for loose in days[1]["loose_snapshots"]], [25])
        # Counted figures only: the live position describes today, not the count day.
        self.assertFalse(
            _keys(days) & {"packets_available", "reserved", "consumed", "available"}
        )
        self.assertFalse(_keys(resp.data) & AUDIT_KEYS)
        self.assertEqual(_documented_keys_mismatches(ExportInventorySnapshotsResponseSerializer(), resp.data), [])
