"""ORM-backed tests for the crop endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own app admin in ``setUpTestData``. Request/response
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
        """Build an app admin and a seeded crop."""
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

    # -- helpers --------------------------------------------------------------

    def _url(self, crop):
        """Return the update/delete URL for a crop (by primary key)."""
        return f"{CROPS_URL}/{crop.id}"

    # -- creation -------------------------------------------------------------

    def test_admin_create_crop_payload_shape_and_name_normalisation(self):
        """The created row is echoed back, attributed, and its name trimmed.

        tests/test_crop_api.py::CropApiTest::test_admin_create_crop_payload_shape_and_name_normalisation
        """
        self.login_as(self.seed_admin)
        response = self.client.post(CROPS_URL, {"name": "  Rice  "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        crop = response.data

        # The new crop takes the next id after the seeded one. This is a stable
        # assertion because DMLTestCase rewinds every sequence before each test
        # (Postgres does not roll back nextval), so ids do not drift with
        # execution order.
        self.assertEqual(crop["id"], self.crop.id + 1)
        self.assertEqual(crop["name"], "Rice")  # surrounding whitespace stripped

        created = Crop.all_objects.get(pk=crop["id"])
        self.assertEqual(created.name, "Rice")
        self.assertEqual(created.created_by_id, self.seed_admin.id)
        self.assertEqual(Crop.all_objects.filter(name="Rice").count(), 1)

    # -- name validation (shared by create and update) ------------------------

    def test_invalid_crop_names_are_rejected_on_create_and_update(self):
        """Blank, whitespace-only, missing and duplicate names all 400, either verb.

        tests/test_crop_api.py::CropApiTest::test_invalid_crop_names_are_rejected_on_create_and_update
        """
        self.login_as(self.seed_admin)
        Crop.objects.create(name="Rice", created_by=self.seed_admin)

        create_cases = [
            ("empty", {"name": ""}),
            ("whitespace only", {"name": "   "}),
            ("missing", {}),
            ("duplicate", {"name": "Wheat"}),
        ]
        for label, body in create_cases:
            with self.subTest(verb="POST", case=label):
                self.assertEqual(
                    self.client.post(CROPS_URL, body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        update_cases = [
            ("whitespace only", {"name": "   "}),
            ("duplicate of another crop", {"name": "Rice"}),
        ]
        for label, body in update_cases:
            with self.subTest(verb="PATCH", case=label):
                self.assertEqual(
                    self.client.patch(self._url(self.crop), body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    # -- update ---------------------------------------------------------------

    def test_admin_update_crop(self):
        """A rename succeeds, and re-sending the crop's own name is not a duplicate.

        tests/test_crop_api.py::CropApiTest::test_admin_update_crop
        """
        self.login_as(self.seed_admin)
        self.assertEqual(
            self.client.patch(self._url(self.crop), {"name": "Wheat"}, format="json").status_code,
            status.HTTP_200_OK,
        )

        response = self.client.patch(self._url(self.crop), {"name": "Rice"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data, {"id": self.crop.id, "name": "Rice"})
        self.crop.refresh_from_db()
        self.assertEqual(self.crop.name, "Rice")

    # -- deletion -------------------------------------------------------------

    def test_delete_soft_deletes_and_removes_the_crop_from_the_api(self):
        """The row is flagged and attributed, drops out of the list, and 404s after.

        tests/test_crop_api.py::CropApiTest::test_delete_soft_deletes_and_removes_the_crop_from_the_api
        """
        self.login_as(self.seed_admin)
        created = self.client.post(CROPS_URL, {"name": "Rice"}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        self.assertEqual(
            self.client.delete(self._url(self.crop)).status_code, status.HTTP_204_NO_CONTENT
        )
        self.crop.refresh_from_db()
        self.assertTrue(self.crop.is_deleted)
        self.assertEqual(self.crop.deleted_by_id, self.seed_admin.id)

        listing = self.client.get(CROPS_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item["name"] == "Rice" for item in listing.data))
        self.assertFalse(any(item.get("name") == "Wheat" for item in listing.data))

    def test_an_unknown_or_deleted_crop_is_404_for_both_verbs(self):
        """tests/test_crop_api.py::CropApiTest::test_an_unknown_or_deleted_crop_is_404_for_both_verbs"""
        self.login_as(self.seed_admin)
        self.client.delete(self._url(self.crop))

        for label, url in (
            ("unknown id", f"{CROPS_URL}/999999"),
            ("soft-deleted crop", self._url(self.crop)),
        ):
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.patch(url, {"name": "Rice"}, format="json").status_code,
                    status.HTTP_404_NOT_FOUND,
                )
                self.assertEqual(
                    self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND
                )
