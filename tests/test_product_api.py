"""ORM-backed tests for the product endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own crop + profiles in ``setUpTestData``. Requests/response flows are
exercised over the test :class:`~rest_framework.test.APIClient` with a logged-in
session, since these are session-only web endpoints.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers, status

from aggregator.models import Crop, Product, Stage, StageIds
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

PRODUCTS_URL = "/api/sales-admin/products"


class ProductApiTest(WebApiTestCase):
    """Cover permission gating and CRUD for the admin-only product endpoints.

    tests/test_product_api.py::ProductApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build a crop, an app admin and a seeded product."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)

        cls.seed_admin = User.objects.create_user(
            phone_number="7777777777",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(
            user=cls.seed_admin, can_update_stock_count=True, created_by=cls.superuser
        )

        cls.crop = Crop.objects.create(name="Wheat", created_by=cls.seed_admin)
        cls.breeder = Stage.by_id(StageIds.BREEDER)
        cls.certificate = Stage.by_id(StageIds.CERTIFICATE)
        cls.product = Product.objects.create(
            name="Premium",
            crop=cls.crop,
            stage=cls.breeder,
            selling_price=1200,
            created_by=cls.seed_admin,
        )

    # -- helpers --------------------------------------------------------------

    def _payload(self, name="Premium"):
        """Return a valid create-product body."""
        return {
            "name": name,
            "crop": self.crop.id,
            "stage": self.breeder.id,
            "selling_price": "1200.00",
        }

    def _url(self, product):
        """Return the update/delete URL for a product (by public id)."""
        return f"{PRODUCTS_URL}/{product.public_id}"

    @staticmethod
    def _png(name="pic.png"):
        """A real 1x1 PNG — ``serializers.ImageField`` verifies content with Pillow."""
        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (1, 1)).save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    @staticmethod
    def _stored(image_url):
        """The file on disk behind a local-backend ``image_url``."""
        return Path(settings.MEDIA_ROOT) / image_url[len(settings.MEDIA_URL):]

    # -- creation -------------------------------------------------------------

    def test_admin_create_product_payload_shape(self):
        """tests/test_product_api.py::ProductApiTest::test_admin_create_product_payload_shape"""
        self.login_as(self.seed_admin)
        response = self.client.post(PRODUCTS_URL, self._payload("Basmati"), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        product = response.data

        self.assertTrue(product["public_id"].startswith("P-"))
        self.assertEqual(product["name"], "Basmati")
        self.assertEqual(product["crop"], {"id": self.crop.id, "name": "Wheat"})
        self.assertEqual(
            product["stage"],
            {"id": self.breeder.id, "code": "BREEDER", "name": "Breeder"},
        )
        self.assertEqual(float(product["selling_price"]), 1200.0)
        self.assertEqual(product["image_url"], "")
        # Buying price is no longer tracked.
        self.assertNotIn("buying_price", product)
        self.assertNotIn("margin_per_packet", product)
        # The primary key must never be sent out.
        self.assertNotIn("id", product)

        created = Product.all_objects.get(public_id=product["public_id"])
        self.assertEqual(created.name, "Basmati")
        self.assertEqual(created.created_by_id, self.seed_admin.id)
        # No image was sent, so nothing was written to disk at all.
        self.assertFalse(Path(settings.MEDIA_ROOT).exists())

    def test_invalid_product_payloads_are_rejected(self):
        """Every field-level rule refuses the write, on create and on update.

        tests/test_product_api.py::ProductApiTest::test_invalid_product_payloads_are_rejected
        """
        self.login_as(self.seed_admin)

        create_cases = [
            ("unknown crop", {"crop": 999999}),
            ("negative selling price", {"selling_price": "-1.00"}),
            ("unknown stage", {"stage": 999999}),
            ("missing stage", {"stage": None}),
        ]
        for label, overrides in create_cases:
            with self.subTest(verb="POST", case=label):
                payload = self._payload(f"Invalid {label}")
                for key, value in overrides.items():
                    if value is None:
                        del payload[key]
                    else:
                        payload[key] = value
                response = self.client.post(PRODUCTS_URL, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                if label == "missing stage":
                    self.assertIn("Stage is required.", response.data["detail"])

        # (name, crop) is unique, on both verbs: "Premium" is the seeded product.
        with self.subTest(verb="POST", case="duplicate name+crop"):
            self.assertEqual(
                self.client.post(PRODUCTS_URL, self._payload("Premium"), format="json").status_code,
                status.HTTP_400_BAD_REQUEST,
            )
        Product.objects.create(
            name="Basmati",
            crop=self.crop,
            stage=self.breeder,
            selling_price=1200,
            created_by=self.seed_admin,
        )
        with self.subTest(verb="PATCH", case="duplicate name+crop"):
            self.assertEqual(
                self.client.patch(
                    self._url(self.product), {"name": "Basmati"}, format="json"
                ).status_code,
                status.HTTP_400_BAD_REQUEST,
            )

    # -- images ---------------------------------------------------------------
    #
    # Supabase is unconfigured in CI, so ``common.storage`` selects the on-disk
    # backend and these exercise it for real; ``tests/conftest.py`` points
    # MEDIA_ROOT at a temp directory per test.

    def test_create_product_with_image_stores_it_and_returns_its_url(self):
        """tests/test_product_api.py::ProductApiTest::test_create_product_with_image_stores_it_and_returns_its_url"""
        self.login_as(self.seed_admin)
        payload = self._payload("Pictured")
        payload["image"] = self._png()
        response = self.client.post(PRODUCTS_URL, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        image_url = response.data["image_url"]
        self.assertTrue(image_url.startswith(f"{settings.MEDIA_URL}products/"))
        self.assertTrue(self._stored(image_url).is_file())

        created = Product.objects.get(public_id=response.data["public_id"])
        self.assertEqual(created.image_url, image_url)

    def test_update_product_replaces_the_image_and_removes_the_old_file(self):
        """tests/test_product_api.py::ProductApiTest::test_update_product_replaces_the_image_and_removes_the_old_file"""
        self.login_as(self.seed_admin)
        created = self.client.post(
            PRODUCTS_URL, {**self._payload("Pictured"), "image": self._png()},
            format="multipart",
        )
        old_url = created.data["image_url"]
        self.assertTrue(self._stored(old_url).is_file())

        response = self.client.patch(
            f"{PRODUCTS_URL}/{created.data['public_id']}",
            {"image": self._png()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        new_url = response.data["image_url"]
        self.assertNotEqual(new_url, old_url)
        self.assertTrue(self._stored(new_url).is_file())
        self.assertFalse(self._stored(old_url).exists())

    def test_create_product_with_a_non_image_file_rejected(self):
        """tests/test_product_api.py::ProductApiTest::test_create_product_with_a_non_image_file_rejected"""
        self.login_as(self.seed_admin)
        payload = self._payload("Not a picture")
        payload["image"] = SimpleUploadedFile(
            "notes.txt", b"definitely not a png", content_type="text/plain"
        )
        response = self.client.post(PRODUCTS_URL, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Product.all_objects.filter(name="Not a picture").exists())

    def test_failed_upload_does_not_create_a_product(self):
        """tests/test_product_api.py::ProductApiTest::test_failed_upload_does_not_create_a_product"""
        self.login_as(self.seed_admin)
        payload = self._payload("Doomed")
        payload["image"] = self._png()
        with patch(
            "api.sales_admin.ProductsView.upload_image",
            side_effect=serializers.ValidationError("Could not upload the image."),
        ):
            response = self.client.post(PRODUCTS_URL, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Product.all_objects.filter(name="Doomed").exists())

    # -- listing --------------------------------------------------------------

    def test_list_products_excludes_deleted(self):
        """tests/test_product_api.py::ProductApiTest::test_list_products_excludes_deleted"""
        self.login_as(self.seed_admin)
        created = self.client.post(PRODUCTS_URL, self._payload("Basmati"), format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        self.client.delete(self._url(self.product))

        response = self.client.get(PRODUCTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        products = response.data
        self.assertTrue(any(item["name"] == "Basmati" for item in products))
        self.assertFalse(any(item.get("name") == "Premium" for item in products))
        for item in products:
            self.assertTrue(item["public_id"].startswith("P-"))
            self.assertIn("crop", item)
            self.assertNotIn("id", item)

    # -- update ---------------------------------------------------------------

    def test_admin_update_product(self):
        """Price and stage are both patchable, echoed back and persisted.

        tests/test_product_api.py::ProductApiTest::test_admin_update_product
        """
        self.login_as(self.seed_admin)
        response = self.client.patch(
            self._url(self.product),
            {"selling_price": "1500.00", "stage": self.certificate.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(float(response.data["selling_price"]), 1500.0)
        self.assertEqual(response.data["stage"]["code"], "CERTIFICATE")

        self.product.refresh_from_db()
        self.assertEqual(self.product.selling_price, 1500)
        self.assertEqual(self.product.stage_id, self.certificate.id)

    # -- deletion -------------------------------------------------------------

    def test_admin_delete_product_soft_deletes(self):
        """tests/test_product_api.py::ProductApiTest::test_admin_delete_product_soft_deletes"""
        self.login_as(self.seed_admin)
        response = self.client.delete(self._url(self.product))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted)
        self.assertEqual(self.product.deleted_by_id, self.seed_admin.id)

    def test_an_unknown_or_deleted_product_is_404_for_both_verbs(self):
        """tests/test_product_api.py::ProductApiTest::test_an_unknown_or_deleted_product_is_404_for_both_verbs"""
        self.login_as(self.seed_admin)
        self.client.delete(self._url(self.product))

        for label, url in (
            ("unknown public_id", f"{PRODUCTS_URL}/P-BOGUSID"),
            ("soft-deleted product", self._url(self.product)),
        ):
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.patch(url, {"name": "X"}, format="json").status_code,
                    status.HTTP_404_NOT_FOUND,
                )
                self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)

