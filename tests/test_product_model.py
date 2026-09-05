"""Product / ProductPackaging model + ProductOperations tests.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

from decimal import Decimal

from aggregator.models import Crop
from aggregator.ProductOperations import add_packaging, create_product, product_payload
from authentication.models import User
from tests.common import DMLTestCase


class ProductModelTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(pk=1)

    def test_create_product_makes_crop_and_public_id(self):
        """tests/test_product_model.py::ProductModelTest::test_create_product_makes_crop_and_public_id"""
        product = create_product(
            name="Hybrid Maize",
            crop="Maize",
            buying_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
            actor=self.su,
        )
        assert product.public_id.startswith("P-")
        assert len(product.public_id) == 14
        assert isinstance(product.crop, Crop)
        assert product.crop.name == "Maize"
        assert product.margin_per_bag == Decimal("50.00")

    def test_crop_is_reused(self):
        """tests/test_product_model.py::ProductModelTest::test_crop_is_reused"""
        one = Decimal("1")
        two = Decimal("2")
        create_product(name="A", crop="Wheat", buying_price=one, selling_price=two, actor=self.su)
        create_product(name="B", crop="Wheat", buying_price=one, selling_price=two, actor=self.su)
        assert Crop.objects.filter(name="Wheat").count() == 1

    def test_packaging_public_id_and_total_weight(self):
        """tests/test_product_model.py::ProductModelTest::test_packaging_public_id_and_total_weight"""
        product = create_product(
            name="Hybrid Maize",
            crop="Maize",
            buying_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
            actor=self.su,
        )
        packaging = add_packaging(
            product, packing_bag_weight=Decimal("25.000"), packing_bags=4, actor=self.su
        )
        assert packaging.public_id.startswith("PP-")
        assert len(packaging.public_id) == 15
        assert packaging.total_weight == Decimal("100.000")

    def test_product_payload_has_no_pk(self):
        """tests/test_product_model.py::ProductModelTest::test_product_payload_has_no_pk"""
        product = create_product(
            name="Hybrid Maize",
            crop="Maize",
            buying_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
            actor=self.su,
        )
        payload = product_payload(product)
        assert "id" not in payload
        assert payload["public_id"] == product.public_id
        assert payload["crop"] == "Maize"
