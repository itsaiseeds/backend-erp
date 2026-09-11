"""Order / OrderItem model + OrderOperations tests.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.utils import IntegrityError

from aggregator.ClientOperations import add_client_address, create_client
from aggregator.InventoryOperations import record_stock_counts
from aggregator.models import (
    Address,
    City,
    Country,
    DispatchDetails,
    Order,
    Pincode,
    PrivateDispatchDetails,
    ProductPackaging,
    Stage,
    StageIds,
    State,
    StatusIds,
)
from aggregator.OrderOperations import (
    attach_dispatch_details,
    create_order,
    order_payload,
    unverify_order,
    update_order_status,
    verify_order,
)
from aggregator.ProductOperations import add_packaging, create_product
from authentication.models import Admin, SalesPerson, User
from tests.common import DMLTestCase


class OrderModelTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.sp_user = User.objects.create_user(
            "9000000001", "Sales Person", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.adm_user = User.objects.create_user(
            "9000000002", "Sales Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.plain_user = User.objects.create_user(
            "9000000003", "Plain User", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.su}
        )
        cls.state = State.objects.create(name="Maharashtra", country=cls.country, created_by=cls.su)
        cls.city = City.objects.create(name="Pune", state=cls.state, created_by=cls.su)
        cls.city2 = City.objects.create(name="Mumbai", state=cls.state, created_by=cls.su)
        cls.pincode = Pincode.objects.create(code="411001", city=cls.city, created_by=cls.su)
        SalesPerson.objects.create(user=cls.sp_user, city=cls.city, created_by=cls.su)
        Admin.objects.create(
            user=cls.adm_user, created_by=cls.su, can_update_stock_count=True
        )

        cls.addr = Address.objects.create(
            address_line_1="1 Main St", pincode=cls.pincode, city=cls.city,
            state=cls.state, country=cls.country, created_by=cls.su,
        )
        cls.addr_other = Address.objects.create(
            address_line_1="9 Other St", pincode=cls.pincode, city=cls.city,
            state=cls.state, country=cls.country, created_by=cls.su,
        )
        cls.client_obj = create_client(
            company_name="Acme", gst_number="27AAPFU0939F1ZV", actor=cls.sp_user
        )
        add_client_address(cls.client_obj, cls.addr, cls.sp_user, is_primary=True)
        cls.product = create_product(
            name="Hybrid Maize", crop="Maize",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("150.00"), actor=cls.sp_user,
        )
        cls.pack = add_packaging(
            cls.product, packet_weight=Decimal("25.000"), packets=4,
            actor=cls.sp_user,
        )

    def _items(self, price="140.00", quantity=3):
        return [
            {
                "product_packaging": self.pack,
                "negotiated_selling_price": Decimal(price),
                "quantity": quantity,
            }
        ]

    def _order(self):
        return create_order(
            client=self.client_obj,
            delivery_address=self.addr,
            actor=self.sp_user,
            items=self._items(),
        )

    def test_create_order_defaults(self):
        """tests/test_order_model.py::OrderModelTest::test_create_order_defaults"""
        order = self._order()
        assert order.public_id.startswith("ORD-")
        assert len(order.public_id) == 16
        assert order.status.code == "BOOKED"
        assert order.expected_delivery_date == datetime.date.today() + datetime.timedelta(days=1)
        # negotiated_selling_price (140) is now per-packaging (was per-packet);
        # line_total = 140 * 3 quantity = 420. total_packets still counts packets.
        assert order.total_amount == Decimal("420.00")
        assert order.total_packets == 12

    def test_delivery_address_must_belong_to_client(self):
        """tests/test_order_model.py::OrderModelTest::test_delivery_address_must_belong_to_client"""
        with self.assertRaises(ValidationError):
            create_order(
                client=self.client_obj,
                delivery_address=self.addr_other,
                actor=self.sp_user,
                items=self._items(price="1", quantity=1),
            )

    def test_order_creator_must_be_salesperson(self):
        """tests/test_order_model.py::OrderModelTest::test_order_creator_must_be_salesperson"""
        with self.assertRaises(ValidationError):
            create_order(
                client=self.client_obj,
                delivery_address=self.addr,
                actor=self.plain_user,
                items=self._items(price="1", quantity=1),
            )

    def test_both_dispatch_details_forbidden_by_db(self):
        """tests/test_order_model.py::OrderModelTest::test_both_dispatch_details_forbidden_by_db"""
        order = self._order()
        d = DispatchDetails.objects.create(
            client=self.client_obj, dispatched_by=self.adm_user,
            dispatch_date=datetime.date.today(),
            from_city=self.city, to_city=self.city2, lr_number="LR1",
        )
        pd = PrivateDispatchDetails.objects.create(
            client=self.client_obj, dispatched_by=self.adm_user,
            dispatch_date=datetime.date.today(),
            from_city=self.city, to_city=self.city2, vehicle_number="MH01",
            driver_number="9800000000",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Order.objects.filter(id=order.id).update(
                    dispatch_details=d, private_dispatch_details=pd
                )

    def test_dispatched_status_requires_dispatch(self):
        """tests/test_order_model.py::OrderModelTest::test_dispatched_status_requires_dispatch"""
        order = self._order()
        with self.assertRaises(ValidationError):
            update_order_status(order, StatusIds.DISPATCHED)

    def test_attach_dispatch_then_dispatch(self):
        """tests/test_order_model.py::OrderModelTest::test_attach_dispatch_then_dispatch"""
        order = self._order()
        attach_dispatch_details(
            order, dispatched_by=self.adm_user, dispatch_date=datetime.date.today(),
            from_city=self.city, to_city=self.city2, lr_number="LR100",
        )
        update_order_status(order, StatusIds.DISPATCHED)
        assert order.status.code == "DISPATCHED"
        assert order.active_dispatch is not None

    def test_dispatch_by_non_admin_rejected(self):
        """tests/test_order_model.py::OrderModelTest::test_dispatch_by_non_admin_rejected"""
        order = self._order()
        with self.assertRaises(ValidationError):
            attach_dispatch_details(
                order, dispatched_by=self.plain_user, dispatch_date=datetime.date.today(),
                from_city=self.city, to_city=self.city2, lr_number="LRX",
            )

    def test_order_payload_has_no_pk(self):
        """tests/test_order_model.py::OrderModelTest::test_order_payload_has_no_pk"""
        order = self._order()
        payload = order_payload(order)
        assert "id" not in payload
        assert payload["public_id"] == order.public_id
        assert payload["items"][0]["packaging"]["public_id"] == self.pack.public_id

    # -- verification ---------------------------------------------------------

    def _count_stock(self):
        """Upload a complete stock count so verification is allowed."""
        record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), 500),
            actor=self.adm_user,
        )

    def test_confirmed_requires_verification_details(self):
        """tests/test_order_model.py::OrderModelTest::test_confirmed_requires_verification_details"""
        order = self._order()
        with self.assertRaises(ValidationError):
            update_order_status(order, StatusIds.CONFIRMED)

    def test_verifier_must_be_admin(self):
        """tests/test_order_model.py::OrderModelTest::test_verifier_must_be_admin"""
        self._count_stock()
        order = self._order()
        with self.assertRaises(PermissionDenied):
            verify_order(order, self.plain_user)

    def test_verify_order_records_who_and_when(self):
        """tests/test_order_model.py::OrderModelTest::test_verify_order_records_who_and_when"""
        self._count_stock()
        order = self._order()
        verify_order(order, self.adm_user)
        assert order.status.code == "CONFIRMED"
        assert order.is_verified
        assert order.verified_by_id == self.adm_user.id
        assert order.verified_at is not None

    def test_verify_order_blocked_without_a_stock_count(self):
        """tests/test_order_model.py::OrderModelTest::test_verify_order_blocked_without_a_stock_count"""
        order = self._order()
        with self.assertRaises(ValidationError):
            verify_order(order, self.adm_user)

    def test_unverify_clears_the_verification_details(self):
        """tests/test_order_model.py::OrderModelTest::test_unverify_clears_the_verification_details"""
        self._count_stock()
        order = self._order()
        verify_order(order, self.adm_user)
        unverify_order(order)
        assert order.status.code == "UNDER_REVIEW"
        assert order.verified_by_id is None
        assert order.verified_at is None
