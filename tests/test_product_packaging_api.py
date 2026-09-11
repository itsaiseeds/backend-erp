"""ORM-backed tests for the product-packaging endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own crop, product + profiles in ``setUpTestData``. Request/response
flows are exercised over the test :class:`~rest_framework.test.APIClient` with a
logged-in session, since these are session-only web endpoints.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import Crop, Product, ProductPackaging, Stage, StageIds
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

PACKAGINGS_URL = "/api/sales-admin/product-packagings"


class ProductPackagingApiTest(WebApiTestCase):
    """Cover permission gating and CRUD for the admin-only packaging endpoints.

    tests/test_product_packaging_api.py::ProductPackagingApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin, a plain user, a crop and a product."""
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
            stage=Stage.by_id(StageIds.BREEDER),
            selling_price=1200,
            created_by=cls.seed_admin,
        )
        cls.packaging = ProductPackaging.objects.create(
            product=cls.product,
            packet_weight=25,
            packets=5,
            selling_price=6000,
            created_by=cls.seed_admin,
        )

    # -- helpers --------------------------------------------------------------

    def _payload(self, product=None, weight=25, packets=5, selling_price="6000.00"):
        """Return a valid create-packaging body."""
        return {
            "product": (product or self.product).public_id,
            "packet_weight": weight,
            "packets": packets,
            "selling_price": selling_price,
        }

    def _url(self, packaging):
        """Return the update/delete URL for a packaging (by public id)."""
        return f"{PACKAGINGS_URL}/{packaging.public_id}"

    # -- permission gating ----------------------------------------------------

    def test_anonymous_requests_are_rejected(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_anonymous_requests_are_rejected"""
        self.assertIn(self.client.get(PACKAGINGS_URL).status_code, (401, 403))
        self.assertIn(
            self.client.post(PACKAGINGS_URL, self._payload(), format="json").status_code,
            (401, 403),
        )
        self.assertIn(
            self.client.patch(
                self._url(self.packaging), {"selling_price": "7000.00"}, format="json"
            ).status_code,
            (401, 403),
        )
        self.assertIn(self.client.delete(self._url(self.packaging)).status_code, (401, 403))

    def test_non_admin_requests_are_rejected(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_non_admin_requests_are_rejected"""
        self.login_as(self.plain)
        self.assertEqual(self.client.get(PACKAGINGS_URL).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.post(PACKAGINGS_URL, self._payload(), format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(
                self._url(self.packaging), {"selling_price": "7000.00"}, format="json"
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self._url(self.packaging)).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    # -- creation -------------------------------------------------------------

    def test_admin_create_packaging_payload_shape(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_admin_create_packaging_payload_shape"""
        self.login_as(self.seed_admin)
        response = self.client.post(
            PACKAGINGS_URL,
            self._payload(weight=50, packets=2, selling_price="3000.00"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        packaging = response.data

        self.assertTrue(packaging["public_id"].startswith("PP-"))
        self.assertEqual(
            packaging["product"],
            {"public_id": self.product.public_id, "name": "Premium"},
        )
        self.assertEqual(float(packaging["packet_weight"]), 50.0)
        self.assertEqual(packaging["packets"], 2)
        self.assertEqual(float(packaging["total_weight"]), 100.0)
        self.assertEqual(float(packaging["selling_price"]), 3000.0)
        # The primary key must never be sent out.
        self.assertNotIn("id", packaging)
        self.assertNotIn("product_id", packaging)

        created = ProductPackaging.all_objects.get(public_id=packaging["public_id"])
        self.assertEqual(created.product_id, self.product.id)
        self.assertEqual(created.created_by_id, self.seed_admin.id)

    def test_admin_create_packaging_defaults_selling_price_to_packets_times_product_price(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_admin_create_packaging_defaults_selling_price_to_packets_times_product_price"""
        self.login_as(self.seed_admin)
        payload = self._payload(weight=50, packets=3)
        payload.pop("selling_price")
        response = self.client.post(PACKAGINGS_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(float(response.data["selling_price"]), 3600.0)

    def test_create_packaging_invalid_product_public_id_rejected(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_create_packaging_invalid_product_public_id_rejected"""
        self.login_as(self.seed_admin)
        payload = self._payload()
        payload["product"] = "P-BOGUSID"
        self.assertEqual(
            self.client.post(PACKAGINGS_URL, payload, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_packaging_duplicate_rejected(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_create_packaging_duplicate_rejected"""
        self.login_as(self.seed_admin)
        self.assertEqual(
            self.client.post(
                PACKAGINGS_URL, self._payload(weight=25, packets=5), format="json"
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_create_packaging_invalid_values_rejected(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_create_packaging_invalid_values_rejected"""
        self.login_as(self.seed_admin)
        for payload in (
            self._payload(weight=0),
            self._payload(weight=-1),
            self._payload(packets=0),
            self._payload(selling_price="-1.00"),
        ):
            self.assertEqual(
                self.client.post(PACKAGINGS_URL, payload, format="json").status_code,
                status.HTTP_400_BAD_REQUEST,
                payload,
            )

    # -- listing --------------------------------------------------------------

    def test_list_packagings_excludes_deleted(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_list_packagings_excludes_deleted"""
        self.login_as(self.seed_admin)
        created = self.client.post(
            PACKAGINGS_URL,
            self._payload(weight=50, packets=2, selling_price="3000.00"),
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        self.client.delete(self._url(self.packaging))

        response = self.client.get(PACKAGINGS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        packagings = response.data
        self.assertTrue(
            any(item["public_id"] == created.data["public_id"] for item in packagings)
        )
        self.assertFalse(
            any(item["public_id"] == self.packaging.public_id for item in packagings)
        )
        for item in packagings:
            self.assertTrue(item["public_id"].startswith("PP-"))
            self.assertIn("product", item)
            self.assertNotIn("id", item)

    # -- update ---------------------------------------------------------------

    def test_admin_update_packaging(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_admin_update_packaging"""
        self.login_as(self.seed_admin)
        response = self.client.patch(
            self._url(self.packaging), {"selling_price": "7000.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(float(response.data["selling_price"]), 7000.0)

        self.packaging.refresh_from_db()
        self.assertEqual(self.packaging.selling_price, 7000)

    def test_update_packaging_own_values_are_allowed(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_update_packaging_own_values_are_allowed"""
        self.login_as(self.seed_admin)
        response = self.client.patch(
            self._url(self.packaging),
            {"packet_weight": 25, "packets": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_packaging_duplicate_rejected(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_update_packaging_duplicate_rejected"""
        ProductPackaging.objects.create(
            product=self.product,
            packet_weight=50,
            packets=2,
            selling_price=3000,
            created_by=self.seed_admin,
        )
        self.login_as(self.seed_admin)
        response = self.client.patch(
            self._url(self.packaging),
            {"packet_weight": 50, "packets": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_packaging_unknown_public_id_not_found(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_update_packaging_unknown_public_id_not_found"""
        self.login_as(self.seed_admin)
        for method in (self.client.patch, self.client.delete):
            self.assertEqual(
                method(
                    f"{PACKAGINGS_URL}/PP-BOGUSID", {"selling_price": "7000.00"}, format="json"
                ).status_code,
                status.HTTP_404_NOT_FOUND,
            )

    # -- deletion -------------------------------------------------------------

    def test_admin_delete_packaging_soft_deletes(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_admin_delete_packaging_soft_deletes"""
        self.login_as(self.seed_admin)
        response = self.client.delete(self._url(self.packaging))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.packaging.refresh_from_db()
        self.assertTrue(self.packaging.is_deleted)
        self.assertEqual(self.packaging.deleted_by_id, self.seed_admin.id)

    def test_deleted_packaging_no_longer_addressable(self):
        """tests/test_product_packaging_api.py::ProductPackagingApiTest::test_deleted_packaging_no_longer_addressable"""
        self.login_as(self.seed_admin)
        self.client.delete(self._url(self.packaging))
        self.assertEqual(
            self.client.patch(
                self._url(self.packaging), {"selling_price": "7000.00"}, format="json"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(self._url(self.packaging)).status_code,
            status.HTTP_404_NOT_FOUND,
        )
