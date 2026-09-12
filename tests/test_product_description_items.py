"""Product feature bullets, written from the sales-admin product endpoints.

The bullets are the marketing copy the Android catalogue renders under a
product card. They are maintained declaratively -- send the whole list and it
replaces what is there -- so the tests below are mostly about what happens to
the rows that were already on the product.

Session-only admin endpoints, so this uses the ``WebApiTestCase`` baseline.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import Crop, Product, ProductDescriptionItem, Stage, StageIds
from aggregator.ProductOperations import (
    description_items_payload,
    sync_product_description_items,
)
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
PRODUCTS_URL = "/api/sales-admin/products"
PRODUCT_URL = "/api/sales-admin/products/{public_id}"

BULLETS = [
    "Yield of best and delicious grains",
    "Plant height of up to 180 to 190 cm",
    "Ripes in 80 to 85 days",
]


class ProductDescriptionItemApiTest(WebApiTestCase):
    """Cover creating, replacing and clearing a product's feature bullets.

    tests/test_product_description_items.py::ProductDescriptionItemApiTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.admin_user = User.objects.create_user(
            phone_number="7777777701",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)

        cls.crop = Crop.objects.create(name="Millet", created_by=cls.admin_user)
        cls.product = Product.objects.create(
            name="Sai-3353",
            crop=cls.crop,
            stage=Stage.by_id(StageIds.CERTIFICATE),
            selling_price=Decimal("250.00"),
            created_by=cls.admin_user,
        )

    # -- helpers --------------------------------------------------------------

    def _create(self, **overrides):
        body = {
            "name": "Sai-33",
            "crop": self.crop.id,
            "stage": Stage.by_id(StageIds.BREEDER).id,
            "selling_price": "120.00",
        }
        body.update(overrides)
        self.login_as(self.admin_user)
        return self.client.post(PRODUCTS_URL, body, format="json")

    def _patch(self, **body):
        self.login_as(self.admin_user)
        return self.client.patch(
            PRODUCT_URL.format(public_id=self.product.public_id), body, format="json"
        )

    def _stored(self):
        """The product's live bullets, in display order."""
        self.product.refresh_from_db()
        return description_items_payload(self.product)

    # -- create ---------------------------------------------------------------

    def test_a_product_is_created_with_its_bullets_in_order(self):
        response = self._create(description_items=BULLETS)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["description_items"], BULLETS)

        created = Product.objects.get(public_id=response.data["public_id"])
        self.assertEqual(
            list(
                created.description_items.order_by("sequence").values_list(
                    "text", "sequence"
                )
            ),
            [(text, index) for index, text in enumerate(BULLETS)],
        )

    def test_bullets_are_optional_on_create(self):
        response = self._create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["description_items"], [])

    def test_a_duplicate_bullet_is_rejected_and_no_product_is_created(self):
        response = self._create(description_items=["Same", "same"])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Duplicate", response.data["detail"])
        self.assertFalse(Product.objects.filter(name="Sai-33").exists())

    def test_a_blank_bullet_is_rejected(self):
        response = self._create(description_items=["Fine", "   "])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- update ---------------------------------------------------------------

    def test_a_new_list_replaces_the_old_one(self):
        sync_product_description_items(self.product, BULLETS, self.admin_user)
        replacement = ["Resistant against more and less rain as well as heat"]

        response = self._patch(description_items=replacement)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["description_items"], replacement)
        self.assertEqual(self._stored(), replacement)

    def test_a_kept_bullet_keeps_its_row_and_is_renumbered(self):
        sync_product_description_items(self.product, BULLETS, self.admin_user)
        kept_id = ProductDescriptionItem.objects.get(
            product=self.product, text=BULLETS[0]
        ).id

        reordered = [BULLETS[2], BULLETS[0]]
        self._patch(description_items=reordered)

        kept = ProductDescriptionItem.objects.get(id=kept_id)
        self.assertEqual(kept.sequence, 1)
        self.assertFalse(kept.is_deleted)
        self.assertEqual(self._stored(), reordered)

    def test_a_dropped_bullet_is_soft_deleted_not_erased(self):
        sync_product_description_items(self.product, BULLETS, self.admin_user)
        self._patch(description_items=BULLETS[:1])

        dropped = ProductDescriptionItem.all_objects.get(
            product=self.product, text=BULLETS[1]
        )
        self.assertTrue(dropped.is_deleted)
        self.assertEqual(dropped.deleted_by, self.admin_user)
        self.assertIsNotNone(dropped.deleted_at)

    def test_a_dropped_bullet_can_be_added_back(self):
        """The unique constraint covers soft-deleted rows, so this must restore."""
        sync_product_description_items(self.product, BULLETS, self.admin_user)
        self._patch(description_items=BULLETS[:1])

        response = self._patch(description_items=BULLETS)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self._stored(), BULLETS)
        self.assertEqual(
            ProductDescriptionItem.all_objects.filter(product=self.product).count(),
            len(BULLETS),
        )

    def test_an_empty_list_clears_every_bullet(self):
        sync_product_description_items(self.product, BULLETS, self.admin_user)

        response = self._patch(description_items=[])
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["description_items"], [])
        self.assertEqual(self._stored(), [])

    def test_omitting_the_field_leaves_the_bullets_untouched(self):
        sync_product_description_items(self.product, BULLETS, self.admin_user)

        response = self._patch(selling_price="999.00")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["description_items"], BULLETS)
        self.assertEqual(self._stored(), BULLETS)

    def test_a_duplicate_bullet_on_update_changes_nothing(self):
        sync_product_description_items(self.product, BULLETS, self.admin_user)

        response = self._patch(description_items=["One", "ONE"])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self._stored(), BULLETS)

    # -- list -----------------------------------------------------------------

    def test_the_product_list_carries_the_bullets(self):
        sync_product_description_items(self.product, BULLETS, self.admin_user)

        self.login_as(self.admin_user)
        response = self.client.get(PRODUCTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(
            item
            for item in response.data
            if item["public_id"] == self.product.public_id
        )
        self.assertEqual(row["description_items"], BULLETS)
