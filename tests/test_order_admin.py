"""Django admin for orders and custom orders: a view of the lifecycle, not a way round it.

An existing order's status, verification, dispatch records and lines are shown
but never written here -- the lifecycle verbs and ``edit-order`` carry the
guards and stock checks. Regular orders are booked from the app, so they cannot
be added here at all. Custom orders have no other screen, so they are still
added here, with the same loose-stock gate ``create_custom_order`` applies.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import add_client_address, create_client
from aggregator.CustomOrderOperations import create_custom_order
from aggregator.models import (
    Address,
    City,
    Country,
    CustomOrder,
    Pincode,
    Stage,
    StageIds,
    State,
)
from aggregator.OrderOperations import create_order
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import Admin, SalesPerson
from tests.common import DMLTestCase, book_raw_material_for_every_product

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
CUSTOM_ORDER_ADD_URL = "/admin/aggregator/customorder/add/"


class OrderAdminTest(DMLTestCase):
    """tests/test_order_admin.py::OrderAdminTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.sp_user = User.objects.create_user(
            "9400000001", "Sales Person", created_by=cls.su, verified_by=cls.su,
            is_verified=True,
        )
        cls.stock_admin = User.objects.create_user(
            "9400000002", "Stock Admin", created_by=cls.su, verified_by=cls.su,
            is_verified=True,
        )
        Admin.objects.create(user=cls.stock_admin, created_by=cls.su, can_update_stock_count=True)

        country = Country.objects.get(name="India")
        state = State.objects.get(name="Gujarat", country=country)
        city = City.objects.get(name="Surat", state=state)
        SalesPerson.objects.create(user=cls.sp_user, city=city, created_by=cls.su)
        pincode, _ = Pincode.objects.get_or_create(
            code="395007", city=city, defaults={"created_by": cls.su}
        )
        cls.addr = Address.objects.create(
            address_line_1="9 Admin Rd", pincode=pincode, city=city, state=state,
            country=country, created_by=cls.su,
        )
        cls.client_obj = create_client(
            company_name="Admin Traders", gst_number="27AAPFU0939F1ZV", actor=cls.sp_user
        )
        add_client_address(cls.client_obj, cls.addr, cls.sp_user, is_primary=True)

        cls.product = create_product(
            name="Admin Cotton", crop="Cotton", stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("150.00"), actor=cls.su,
        )
        cls.pack = add_packaging(
            cls.product, packet_weight=Decimal("1.000"), packets=10, actor=cls.su
        )
        cls.weight = Decimal("1.000")
        book_raw_material_for_every_product(actor=cls.su)

    def setUp(self):
        super().setUp()
        inv.record_loose_stock(
            product=self.product, packet_weight=self.weight, packets=50,
            actor=self.stock_admin,
        )
        self.client.force_login(self.su)

    def _add_custom_order(self, *lines):
        data = {
            "client": self.client_obj.id,
            "delivery_address": self.addr.id,
            "expected_delivery_date": "2026-12-01",
            "special_comments": "",
            "deleted_at": "",
            "deleted_by": "",
            "items-TOTAL_FORMS": str(len(lines)),
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "_save": "Save",
        }
        for index, packets in enumerate(lines):
            data.update(
                {
                    f"items-{index}-product": self.product.id,
                    f"items-{index}-packet_weight": "1.000",
                    f"items-{index}-packets": str(packets),
                    f"items-{index}-negotiated_selling_price": "150.00",
                }
            )
        return self.client.post(CUSTOM_ORDER_ADD_URL, data)

    # -- regular orders -------------------------------------------------------

    def test_orders_cannot_be_added_here(self):
        """tests/test_order_admin.py::OrderAdminTest::test_orders_cannot_be_added_here"""
        assert self.client.get("/admin/aggregator/order/add/").status_code == 403

    def test_an_orders_lifecycle_and_lines_are_view_only(self):
        """tests/test_order_admin.py::OrderAdminTest::test_an_orders_lifecycle_and_lines_are_view_only"""
        order = create_order(
            client=self.client_obj, delivery_address=self.addr, actor=self.sp_user,
            items=[{"product_packaging": self.pack, "quantity": 2}],
        )

        response = self.client.get(f"/admin/aggregator/order/{order.pk}/change/")

        assert response.status_code == 200
        editable = response.context["adminform"].form.fields
        for field in ("status", "verified_by", "verified_at", "dispatch_details"):
            assert field not in editable
        lines = response.context["inline_admin_formsets"][0]
        assert not lines.has_add_permission
        assert not lines.has_change_permission
        assert not lines.has_delete_permission

    # -- custom orders --------------------------------------------------------

    def test_a_custom_order_is_added_confirmed_and_reserves_its_packets(self):
        """Adding one is verifying it, as in create_custom_order.

        tests/test_order_admin.py::OrderAdminTest::test_a_custom_order_is_added_confirmed_and_reserves_its_packets
        """
        response = self._add_custom_order(20)

        assert response.status_code == 302, response.content
        order = CustomOrder.objects.get(client=self.client_obj)
        assert order.status.code == "CONFIRMED"
        assert order.verified_by == self.su
        assert order.verified_at is not None
        assert inv.reserved_loose_packets(self.product, self.weight) == 20

    def test_a_custom_order_beyond_loose_stock_is_a_form_error(self):
        """tests/test_order_admin.py::OrderAdminTest::test_a_custom_order_beyond_loose_stock_is_a_form_error"""
        response = self._add_custom_order(60)

        assert response.status_code == 200
        self.assertContains(response, "need 60, have 50")
        assert not CustomOrder.objects.exists()

    def test_a_custom_orders_lines_and_lifecycle_are_fixed_once_added(self):
        """tests/test_order_admin.py::OrderAdminTest::test_a_custom_orders_lines_and_lifecycle_are_fixed_once_added"""
        order = create_custom_order(
            client=self.client_obj, delivery_address=self.addr, actor=self.stock_admin,
            items=[{"product": self.product, "packet_weight": self.weight, "packets": 5}],
        )

        response = self.client.get(f"/admin/aggregator/customorder/{order.pk}/change/")

        assert response.status_code == 200
        assert "status" not in response.context["adminform"].form.fields
        lines = response.context["inline_admin_formsets"][0]
        assert not lines.has_change_permission
        assert not lines.has_delete_permission

    def test_deleting_a_custom_order_holding_stock_is_refused(self):
        """tests/test_order_admin.py::OrderAdminTest::test_deleting_a_custom_order_holding_stock_is_refused"""
        order = create_custom_order(
            client=self.client_obj, delivery_address=self.addr, actor=self.stock_admin,
            items=[{"product": self.product, "packet_weight": self.weight, "packets": 5}],
        )

        response = self.client.post(
            f"/admin/aggregator/customorder/{order.pk}/delete/", {"post": "yes"}, follow=True
        )

        self.assertContains(response, "Cannot delete an order that is CONFIRMED")
        order.refresh_from_db()
        assert not order.is_deleted
