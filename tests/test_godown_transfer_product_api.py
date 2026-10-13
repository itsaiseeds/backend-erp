"""Godown manager product transfer: ``POST /android/api/v1/godown/transfer-product``.

The transfer rules themselves are proven against the admin endpoint in
``tests/test_transfer_product_api.py``; role gating is owned by
``tests/test_view_contracts.py``. This proves the godown endpoint reaches the
same ``InwardOperations.transfer_raw_material`` and returns the same shape.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations as inv
from aggregator.models import Crop, InwardRawMaterial, Product, Stage, StageIds
from tests.android.common import AndroidApiTestCase
from tests.common import book_raw_material

User = get_user_model()

URL = "/android/api/v1/godown/transfer-product"


class GodownTransferProductApiTest(AndroidApiTestCase):
    """tests/test_godown_transfer_product_api.py::GodownTransferProductApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        cls.godown = User.objects.get(phone_number="3333333333")
        cls.crop = Crop.objects.create(name="Godown Transfer Wheat", created_by=cls.superuser)
        cls.other_crop = Crop.objects.create(name="Godown Transfer Rice", created_by=cls.superuser)
        cls.source = cls._product("gtx-33", cls.crop)
        cls.target = cls._product("gtx-balwan", cls.crop)
        cls.foreign = cls._product("gtx-rice", cls.other_crop)

    @classmethod
    def _product(cls, name, crop):
        return Product.objects.create(
            name=name,
            crop=crop,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )

    def setUp(self):
        super().setUp()
        self.login_as(self.godown)

    def _transfer(self, quantity="5", target=None):
        return self.client.post(
            URL,
            {
                "source_product": self.source.public_id,
                "target_product": (target or self.target).public_id,
                "quantity_kg": quantity,
            },
            format="json",
        )

    def test_a_godown_manager_transfers_raw_material(self):
        """tests/test_godown_transfer_product_api.py::GodownTransferProductApiTest::test_a_godown_manager_transfers_raw_material"""
        book_raw_material(self.source, Decimal("100"), actor=self.godown)

        response = self._transfer("5")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["transferred_kg"], "5.000")
        self.assertEqual(response.data["source"]["available_kg"], "95.000")
        self.assertEqual(response.data["target"]["available_kg"], "5.000")
        [booked] = response.data["target_lots"]
        self.assertEqual(booked["product"]["public_id"], self.target.public_id)
        self.assertEqual(booked["quantity_kg"], "5.000")
        self.assertEqual(inv.raw_available_kg(self.source), Decimal("95"))
        self.assertEqual(inv.raw_available_kg(self.target), Decimal("5"))
        lot = InwardRawMaterial.objects.get(product=self.target)
        self.assertEqual(lot.created_by, self.godown)

    def test_the_admin_rules_hold(self):
        """tests/test_godown_transfer_product_api.py::GodownTransferProductApiTest::test_the_admin_rules_hold"""
        book_raw_material(self.source, Decimal("10"), actor=self.godown)

        too_much = self._transfer("11")
        other_crop = self._transfer("5", target=self.foreign)

        self.assertEqual(too_much.status_code, status.HTTP_400_BAD_REQUEST, too_much.data)
        self.assertEqual(other_crop.status_code, status.HTTP_400_BAD_REQUEST, other_crop.data)
        self.assertIn("one crop", str(other_crop.data))
        self.assertEqual(inv.raw_available_kg(self.source), Decimal("10"))
