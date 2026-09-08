"""ORM-backed tests for the product endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own crop + profiles in ``setUpTestData``. Requests/response flows are
exercised over the test :class:`~rest_framework.test.APIClient` with a logged-in
session, since these are session-only web endpoints.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import Crop, Product
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
        """Build a crop, an app admin, a plain user and a seeded product."""
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

        cls.plain = User.objects.create_user(
            phone_number="6666666666",
            name="plain user",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )

        cls.crop = Crop.objects.create(name="Wheat", created_by=cls.seed_admin)
        cls.product = Product.objects.create(
            name="Premium",
            crop=cls.crop,
            buying_price=1000,
            selling_price=1200,
            created_by=cls.seed_admin,
        )

    # -- helpers --------------------------------------------------------------

    def _payload(self, name="Premium"):
        """Return a valid create-product body."""
        return {
            "name": name,
            "crop": self.crop.id,
            "buying_price": "1000.00",
            "selling_price": "1200.00",
        }

    def _url(self, product):
        """Return the update/delete URL for a product (by public id)."""
        return f"{PRODUCTS_URL}/{product.public_id}"

    # -- permission gating ----------------------------------------------------

    def test_anonymous_requests_are_rejected(self):
        """tests/test_product_api.py::ProductApiTest::test_anonymous_requests_are_rejected"""
        self.assertIn(self.client.get(PRODUCTS_URL).status_code, (401, 403))
        self.assertIn(
            self.client.post(PRODUCTS_URL, self._payload(), format="json").status_code,
            (401, 403),
        )
        self.assertIn(
            self.client.patch(self._url(self.product), {"name": "X"}, format="json").status_code,
            (401, 403),
        )
        self.assertIn(self.client.delete(self._url(self.product)).status_code, (401, 403))

    def test_non_admin_requests_are_rejected(self):
        """tests/test_product_api.py::ProductApiTest::test_non_admin_requests_are_rejected"""
        self.login_as(self.plain)
        self.assertEqual(self.client.get(PRODUCTS_URL).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.post(PRODUCTS_URL, self._payload(), format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(self._url(self.product), {"name": "X"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self._url(self.product)).status_code, status.HTTP_403_FORBIDDEN
        )

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
        self.assertEqual(float(product["buying_price"]), 1000.0)
        self.assertEqual(float(product["selling_price"]), 1200.0)
        self.assertEqual(float(product["margin_per_packet"]), 200.0)
        # The primary key must never be sent out.
        self.assertNotIn("id", product)

        created = Product.all_objects.get(public_id=product["public_id"])
        self.assertEqual(created.name, "Basmati")
        self.assertEqual(created.created_by_id, self.seed_admin.id)

    def test_create_product_invalid_crop_rejected(self):
        """tests/test_product_api.py::ProductApiTest::test_create_product_invalid_crop_rejected"""
        self.login_as(self.seed_admin)
        payload = self._payload()
        payload["crop"] = 999999
        self.assertEqual(
            self.client.post(PRODUCTS_URL, payload, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_product_duplicate_name_crop_rejected(self):
        """tests/test_product_api.py::ProductApiTest::test_create_product_duplicate_name_crop_rejected"""
        self.login_as(self.seed_admin)
        self.assertEqual(
            self.client.post(PRODUCTS_URL, self._payload("Premium"), format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_product_negative_prices_rejected(self):
        """tests/test_product_api.py::ProductApiTest::test_create_product_negative_prices_rejected"""
        self.login_as(self.seed_admin)
        for key in ("buying_price", "selling_price"):
            payload = self._payload(f"Product-{key}")
            payload[key] = "-1.00"
            self.assertEqual(
                self.client.post(PRODUCTS_URL, payload, format="json").status_code,
                status.HTTP_400_BAD_REQUEST,
                key,
            )

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
        """tests/test_product_api.py::ProductApiTest::test_admin_update_product"""
        self.login_as(self.seed_admin)
        response = self.client.patch(
            self._url(self.product), {"selling_price": "1500.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(float(response.data["selling_price"]), 1500.0)

        self.product.refresh_from_db()
        self.assertEqual(self.product.selling_price, 1500)

    def test_update_product_duplicate_name_crop_rejected(self):
        """tests/test_product_api.py::ProductApiTest::test_update_product_duplicate_name_crop_rejected"""
        Product.objects.create(
            name="Basmati",
            crop=self.crop,
            buying_price=1000,
            selling_price=1200,
            created_by=self.seed_admin,
        )
        self.login_as(self.seed_admin)
        response = self.client.patch(
            self._url(self.product), {"name": "Basmati"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_product_unknown_public_id_not_found(self):
        """tests/test_product_api.py::ProductApiTest::test_update_product_unknown_public_id_not_found"""
        self.login_as(self.seed_admin)
        for method in (self.client.patch, self.client.delete):
            self.assertEqual(
                method(f"{PRODUCTS_URL}/P-BOGUSID", {"name": "X"}, format="json").status_code,
                status.HTTP_404_NOT_FOUND,
            )

    # -- deletion -------------------------------------------------------------

    def test_admin_delete_product_soft_deletes(self):
        """tests/test_product_api.py::ProductApiTest::test_admin_delete_product_soft_deletes"""
        self.login_as(self.seed_admin)
        response = self.client.delete(self._url(self.product))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted)
        self.assertEqual(self.product.deleted_by_id, self.seed_admin.id)

    def test_deleted_product_no_longer_addressable(self):
        """tests/test_product_api.py::ProductApiTest::test_deleted_product_no_longer_addressable"""
        self.login_as(self.seed_admin)
        self.client.delete(self._url(self.product))
        self.assertEqual(
            self.client.patch(self._url(self.product), {"name": "X"}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(self._url(self.product)).status_code,
            status.HTTP_404_NOT_FOUND,
        )
