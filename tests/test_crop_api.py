"""ORM-backed tests for the crop endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own app admin + plain user in ``setUpTestData``. Request/response
flows are exercised over the test :class:`~rest_framework.test.APIClient` with a
logged-in session, since these are session-only web endpoints.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import Crop
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

CROPS_URL = "/api/sales-admin/crops"


class CropApiTest(WebApiTestCase):
    """Cover permission gating and CRUD for the admin-only crop endpoints.

    tests/test_crop_api.py::CropApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin, a plain user and a seeded crop."""
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

    # -- helpers --------------------------------------------------------------

    def _url(self, crop):
        """Return the update/delete URL for a crop (by primary key)."""
        return f"{CROPS_URL}/{crop.id}"

    # -- permission gating ----------------------------------------------------

    def test_anonymous_requests_are_rejected(self):
        """tests/test_crop_api.py::CropApiTest::test_anonymous_requests_are_rejected"""
        self.assertIn(self.client.get(CROPS_URL).status_code, (401, 403))
        self.assertIn(
            self.client.post(CROPS_URL, {"name": "Rice"}, format="json").status_code,
            (401, 403),
        )
        self.assertIn(
            self.client.patch(self._url(self.crop), {"name": "Rice"}, format="json").status_code,
            (401, 403),
        )
        self.assertIn(self.client.delete(self._url(self.crop)).status_code, (401, 403))

    def test_non_admin_requests_are_rejected(self):
        """tests/test_crop_api.py::CropApiTest::test_non_admin_requests_are_rejected"""
        self.login_as(self.plain)
        self.assertEqual(self.client.get(CROPS_URL).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.post(CROPS_URL, {"name": "Rice"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(self._url(self.crop), {"name": "Rice"}, format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(self._url(self.crop)).status_code, status.HTTP_403_FORBIDDEN
        )

    # -- creation -------------------------------------------------------------

    def test_admin_create_crop_payload_shape(self):
        """tests/test_crop_api.py::CropApiTest::test_admin_create_crop_payload_shape"""
        self.login_as(self.seed_admin)
        response = self.client.post(CROPS_URL, {"name": "Rice"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        crop = response.data

        self.assertEqual(crop["id"], self.crop.id + 1)
        self.assertEqual(crop["name"], "Rice")

        created = Crop.all_objects.get(pk=crop["id"])
        self.assertEqual(created.name, "Rice")
        self.assertEqual(created.created_by_id, self.seed_admin.id)

    def test_create_crop_strips_name_whitespace(self):
        """tests/test_crop_api.py::CropApiTest::test_create_crop_strips_name_whitespace"""
        self.login_as(self.seed_admin)
        response = self.client.post(CROPS_URL, {"name": "  Rice  "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data["name"], "Rice")
        self.assertEqual(Crop.all_objects.filter(name="Rice").count(), 1)

    def test_create_crop_blank_name_rejected(self):
        """tests/test_crop_api.py::CropApiTest::test_create_crop_blank_name_rejected"""
        self.login_as(self.seed_admin)
        for body in ({"name": ""}, {"name": "   "}, {}):
            self.assertEqual(
                self.client.post(CROPS_URL, body, format="json").status_code,
                status.HTTP_400_BAD_REQUEST,
                body,
            )

    def test_create_crop_duplicate_name_rejected(self):
        """tests/test_crop_api.py::CropApiTest::test_create_crop_duplicate_name_rejected"""
        self.login_as(self.seed_admin)
        self.assertEqual(
            self.client.post(CROPS_URL, {"name": "Wheat"}, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # -- listing --------------------------------------------------------------

    def test_list_crops_excludes_deleted(self):
        """tests/test_crop_api.py::CropApiTest::test_list_crops_excludes_deleted"""
        self.login_as(self.seed_admin)
        created = self.client.post(CROPS_URL, {"name": "Rice"}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        self.client.delete(self._url(self.crop))

        response = self.client.get(CROPS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        crops = response.data
        self.assertTrue(any(item["name"] == "Rice" for item in crops))
        self.assertFalse(any(item.get("name") == "Wheat" for item in crops))

    # -- update ---------------------------------------------------------------

    def test_admin_update_crop(self):
        """tests/test_crop_api.py::CropApiTest::test_admin_update_crop"""
        self.login_as(self.seed_admin)
        response = self.client.patch(self._url(self.crop), {"name": "Rice"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data, {"id": self.crop.id, "name": "Rice"})

        self.crop.refresh_from_db()
        self.assertEqual(self.crop.name, "Rice")

    def test_update_crop_own_name_is_allowed(self):
        """tests/test_crop_api.py::CropApiTest::test_update_crop_own_name_is_allowed"""
        self.login_as(self.seed_admin)
        response = self.client.patch(self._url(self.crop), {"name": "Wheat"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_crop_duplicate_name_rejected(self):
        """tests/test_crop_api.py::CropApiTest::test_update_crop_duplicate_name_rejected"""
        Crop.objects.create(name="Rice", created_by=self.seed_admin)
        self.login_as(self.seed_admin)
        response = self.client.patch(self._url(self.crop), {"name": "Rice"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_crop_blank_name_rejected(self):
        """tests/test_crop_api.py::CropApiTest::test_update_crop_blank_name_rejected"""
        self.login_as(self.seed_admin)
        response = self.client.patch(self._url(self.crop), {"name": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_crop_unknown_id_not_found(self):
        """tests/test_crop_api.py::CropApiTest::test_update_crop_unknown_id_not_found"""
        self.login_as(self.seed_admin)
        for method in (self.client.patch, self.client.delete):
            self.assertEqual(
                method(f"{CROPS_URL}/999999", {"name": "Rice"}, format="json").status_code,
                status.HTTP_404_NOT_FOUND,
            )

    # -- deletion -------------------------------------------------------------

    def test_admin_delete_crop_soft_deletes(self):
        """tests/test_crop_api.py::CropApiTest::test_admin_delete_crop_soft_deletes"""
        self.login_as(self.seed_admin)
        response = self.client.delete(self._url(self.crop))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.crop.refresh_from_db()
        self.assertTrue(self.crop.is_deleted)
        self.assertEqual(self.crop.deleted_by_id, self.seed_admin.id)

    def test_deleted_crop_no_longer_addressable(self):
        """tests/test_crop_api.py::CropApiTest::test_deleted_crop_no_longer_addressable"""
        self.login_as(self.seed_admin)
        self.client.delete(self._url(self.crop))
        self.assertEqual(
            self.client.patch(self._url(self.crop), {"name": "Rice"}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(self._url(self.crop)).status_code,
            status.HTTP_404_NOT_FOUND,
        )
