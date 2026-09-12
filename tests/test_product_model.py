"""Product / ProductPackaging model + ProductOperations tests.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

from decimal import Decimal

from aggregator.models import Crop, Stage, StageIds
from aggregator.ProductOperations import add_packaging, create_product, product_payload
from authentication.models import User
from tests.common import DMLTestCase


class ProductModelTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)

    def test_create_product_makes_crop_and_public_id(self):
        """tests/test_product_model.py::ProductModelTest::test_create_product_makes_crop_and_public_id"""
        product = create_product(
            name="Hybrid Maize",
            crop="Maize",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("150.00"),
            actor=self.su,
        )
        assert product.public_id.startswith("P-")
        assert len(product.public_id) == 14
        assert isinstance(product.crop, Crop)
        assert product.crop.name == "Maize"
        assert product.stage.code == StageIds.BREEDER.name
        assert product.image_url == ""

    def test_crop_is_reused(self):
        """tests/test_product_model.py::ProductModelTest::test_crop_is_reused"""
        two = Decimal("2")
        breeder = Stage.by_id(StageIds.BREEDER)
        create_product(name="A", crop="Wheat", stage=breeder, selling_price=two, actor=self.su)
        create_product(name="B", crop="Wheat", stage=breeder, selling_price=two, actor=self.su)
        assert Crop.objects.filter(name="Wheat").count() == 1

    def test_packaging_public_id_and_total_weight(self):
        """tests/test_product_model.py::ProductModelTest::test_packaging_public_id_and_total_weight"""
        product = create_product(
            name="Hybrid Maize",
            crop="Maize",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("150.00"),
            actor=self.su,
        )
        packaging = add_packaging(
            product, packet_weight=Decimal("25.000"), packets=4, actor=self.su
        )
        assert packaging.public_id.startswith("PP-")
        assert len(packaging.public_id) == 15
        assert packaging.total_weight == Decimal("100.000")

    def test_product_payload_has_no_pk(self):
        """tests/test_product_model.py::ProductModelTest::test_product_payload_has_no_pk"""
        product = create_product(
            name="Hybrid Maize",
            crop="Maize",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("150.00"),
            actor=self.su,
        )
        payload = product_payload(product)
        assert "id" not in payload
        assert payload["public_id"] == product.public_id
        assert payload["crop"] == "Maize"
        assert payload["stage"] == {"code": "BREEDER", "name": "Breeder"}
        assert payload["image_url"] == ""
        assert "buying_price" not in payload
        assert "margin_per_packet" not in payload

    def test_price_for_weight_scales_the_per_kilogram_rate(self):
        """tests/test_product_model.py::ProductModelTest::test_price_for_weight_scales_the_per_kilogram_rate"""
        product = create_product(
            name="Per Kilo", crop="Wheat",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("150.00"), actor=self.su,
        )
        assert product.price_for_weight(Decimal("1.000")) == Decimal("150.00")
        assert product.price_for_weight(Decimal("0.500")) == Decimal("75.00")
        assert product.price_for_weight(Decimal("2.500")) == Decimal("375.00")

    def test_price_for_weight_rounds_to_paise(self):
        """A per-kg rate on an odd weight must still land on a storable money value.

        tests/test_product_model.py::ProductModelTest::test_price_for_weight_rounds_to_paise
        """
        product = create_product(
            name="Odd Rate", crop="Wheat",
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=Decimal("99.99"), actor=self.su,
        )
        # 99.99 x 0.333 = 33.29667 -> 33.30
        assert product.price_for_weight(Decimal("0.333")) == Decimal("33.30")
