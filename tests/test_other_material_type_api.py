"""ORM-backed tests for the other-material-type endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own app admin in ``setUpTestData``. The three reference types are
seeded by ``dml.sql`` (``bag_outer_cover`` kg id 1, ``packet_outer_cover`` kg id 2,
``leaflets`` count id 3).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import OtherMaterialType
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

TYPES_URL = "/api/sales-admin/other-material-types"


class OtherMaterialTypeApiTest(WebApiTestCase):
    """Cover permission gating and CRUD for the material-type endpoints.

    tests/test_other_material_type_api.py::OtherMaterialTypeApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin; the three reference types come from dml.sql."""
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

        cls.bag_cover = OtherMaterialType.objects.get(name="bag_outer_cover")
        cls.leaflets = OtherMaterialType.objects.get(name="leaflets")

    # -- helpers --------------------------------------------------------------

    def _url(self, material_type):
        """Return the update/delete URL for a material type (by primary key)."""
        return f"{TYPES_URL}/{material_type.id}"

    def _create_type(self, name="sticker", unit_type="count"):
        """POST a material type and return the response."""
        return self.client.post(
            TYPES_URL, {"name": name, "unit_type": unit_type}, format="json"
        )

    # -- listing --------------------------------------------------------------

    def test_list_returns_the_seeded_reference_types(self):
        """tests/test_other_material_type_api.py::OtherMaterialTypeApiTest::test_list_returns_the_seeded_reference_types"""
        self.login_as(self.seed_admin)
        response = self.client.get(TYPES_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [
            {"id": 1, "name": "bag_outer_cover", "unit_type": "kg"},
            {"id": 3, "name": "leaflets", "unit_type": "count"},
            {"id": 2, "name": "packet_outer_cover", "unit_type": "kg"},
        ])

    # -- creation -------------------------------------------------------------

    def test_admin_create_material_type_payload_shape_and_name_normalisation(self):
        """The created row is echoed back, attributed, and its name trimmed.

        tests/test_other_material_type_api.py::OtherMaterialTypeApiTest::test_admin_create_material_type_payload_shape_and_name_normalisation
        """
        self.login_as(self.seed_admin)
        response = self._create_type("  Sticker  ")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        material_type = response.data

        # The seeded setval leaves the sequence at 3, so the first new type is 4.
        self.assertEqual(material_type["id"], self.leaflets.id + 1)
        self.assertEqual(material_type["name"], "Sticker")  # surrounding whitespace stripped
        self.assertEqual(material_type["unit_type"], "count")

        created = OtherMaterialType.all_objects.get(pk=material_type["id"])
        self.assertEqual(created.name, "Sticker")
        self.assertEqual(created.unit_type, "count")
        self.assertEqual(created.created_by_id, self.seed_admin.id)
        self.assertEqual(OtherMaterialType.all_objects.filter(name="Sticker").count(), 1)

    # -- validation (shared by create and update) -----------------------------

    def test_invalid_material_type_data_is_rejected_on_create_and_update(self):
        """Blank, missing, unknown-unit and duplicate bodies all 400.

        tests/test_other_material_type_api.py::OtherMaterialTypeApiTest::test_invalid_material_type_data_is_rejected_on_create_and_update
        """
        self.login_as(self.seed_admin)
        other = OtherMaterialType.objects.create(
            name="packet_outer_cover_custom", unit_type="kg", created_by=self.seed_admin
        )

        create_cases = [
            ("blank name", {"name": "", "unit_type": "count"}),
            ("whitespace only", {"name": "   ", "unit_type": "count"}),
            ("missing", {}),
            ("invalid unit", {"name": "sticker", "unit_type": "units"}),
            ("duplicate of a seed", {"name": "bag_outer_cover", "unit_type": "count"}),
            (
                "duplicate ignoring whitespace",
                {"name": "  bag_outer_cover  ", "unit_type": "kg"},
            ),
        ]
        for label, body in create_cases:
            with self.subTest(verb="POST", case=label):
                self.assertEqual(
                    self.client.post(TYPES_URL, body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        update_cases = [
            ("whitespace only", {"name": "   "}),
            ("invalid unit", {"unit_type": "units"}),
            ("duplicate of another type", {"name": "leaflets"}),
        ]
        for label, body in update_cases:
            with self.subTest(verb="PATCH", case=label):
                self.assertEqual(
                    self.client.patch(self._url(other), body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    # -- update ---------------------------------------------------------------

    def test_admin_update_material_type(self):
        """Name and unit can change; re-sending the type's own name is not a duplicate.

        tests/test_other_material_type_api.py::OtherMaterialTypeApiTest::test_admin_update_material_type
        """
        self.login_as(self.seed_admin)
        response = self.client.patch(
            self._url(self.leaflets), {"name": "Leaflets", "unit_type": "kg"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data, {"id": 3, "name": "Leaflets", "unit_type": "kg"})
        self.leaflets.refresh_from_db()
        self.assertEqual(self.leaflets.name, "Leaflets")
        self.assertEqual(self.leaflets.unit_type, "kg")

        # Re-sending the type's own name is not a duplicate.
        self.assertEqual(
            self.client.patch(self._url(self.leaflets), {"name": "Leaflets"},
                              format="json").status_code,
            status.HTTP_200_OK,
        )

    # -- deletion -------------------------------------------------------------

    def test_delete_soft_deletes_and_removes_the_type_from_the_api(self):
        """The row is flagged and attributed, drops out of the list, and 404s after.

        tests/test_other_material_type_api.py::OtherMaterialTypeApiTest::test_delete_soft_deletes_and_removes_the_type_from_the_api
        """
        self.login_as(self.seed_admin)
        self.assertEqual(
            self.client.delete(self._url(self.bag_cover)).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.bag_cover.refresh_from_db()
        self.assertTrue(self.bag_cover.is_deleted)
        self.assertEqual(self.bag_cover.deleted_by_id, self.seed_admin.id)

        listing = self.client.get(TYPES_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertFalse(any(t["name"] == "bag_outer_cover" for t in listing.data))

    def test_an_unknown_or_deleted_type_is_404_for_both_verbs(self):
        """tests/test_other_material_type_api.py::OtherMaterialTypeApiTest::test_an_unknown_or_deleted_type_is_404_for_both_verbs"""
        self.login_as(self.seed_admin)
        self.client.delete(self._url(self.leaflets))

        for label, url in (
            ("unknown id", f"{TYPES_URL}/999999"),
            ("soft-deleted type", self._url(self.leaflets)),
        ):
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.patch(url, {"name": "X"}, format="json").status_code,
                    status.HTTP_404_NOT_FOUND,
                )
                self.assertEqual(
                    self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND
                )
