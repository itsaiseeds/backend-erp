"""ORM-backed tests for the other-material-recipe endpoints (list/create + delete-ish).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own app admin in ``setUpTestData``. The two products (SAI-33, SAI-3353)
and the three material types come from ``dml.sql``.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import OtherMaterialRecipe, OtherMaterialType, Product
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

RECIPES_URL = "/api/sales-admin/other-material-recipes"


class OtherMaterialRecipeApiTest(WebApiTestCase):
    """Cover permission gating, create/list/delete and the no-PATCH rule.

    tests/test_other_material_recipe_api.py::OtherMaterialRecipeApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin and grab the seeded product / material types."""
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

        cls.product = Product.objects.get(name="SAI-33")
        cls.other_product = Product.objects.get(name="SAI-3353")
        cls.bag_cover = OtherMaterialType.objects.get(name="bag_outer_cover")
        cls.packet_cover = OtherMaterialType.objects.get(name="packet_outer_cover")

    # -- helpers --------------------------------------------------------------

    def _delete_url(self, recipe):
        """Return the delete URL for a recipe (by public id)."""
        return f"/api/sales-admin/other-material-recipe/{recipe['public_id']}"

    def _create_recipe(self, product=None, material_type=None, packet_weight="2.5",
                       quantity="3"):
        """POST a recipe and return the response (product/type default to the fixtures)."""
        return self.client.post(
            RECIPES_URL,
            {
                "product": (product or self.product).id,
                "material_type": (material_type or self.packet_cover).id,
                "packet_weight": packet_weight,
                "quantity": quantity,
            },
            format="json",
        )

    # -- creation -------------------------------------------------------------

    def test_admin_create_recipe_payload_shape(self):
        """The created row is echoed back with its prefixed public id.

        tests/test_other_material_recipe_api.py::OtherMaterialRecipeApiTest::test_admin_create_recipe_payload_shape
        """
        self.login_as(self.seed_admin)
        response = self._create_recipe()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        recipe = response.data

        self.assertTrue(recipe["public_id"].startswith("OMR-"))
        self.assertEqual(recipe["product"], {
            "public_id": "P-I34V7RI1JPUH", "name": "SAI-33",
        })
        self.assertEqual(recipe["material_type"], {
            "id": 2, "name": "packet_outer_cover", "unit_type": "kg",
        })
        self.assertEqual(recipe["packet_weight"], "2.500")
        self.assertEqual(recipe["quantity"], "3.000")

        created = OtherMaterialRecipe.all_objects.get(public_id=recipe["public_id"])
        self.assertEqual(created.created_by_id, self.seed_admin.id)
        self.assertEqual(created.quantity, Decimal("3.000"))

    def test_a_recipe_is_unique_per_product_type_and_packet_weight(self):
        """Same keys 400; changing a variant dimension creates a fresh row.

        tests/test_other_material_recipe_api.py::OtherMaterialRecipeApiTest::test_a_recipe_is_unique_per_product_type_and_packet_weight
        """
        self.login_as(self.seed_admin)
        self.assertEqual(
            self._create_recipe().status_code, status.HTTP_201_CREATED
        )

        self.assertEqual(
            self._create_recipe().status_code, status.HTTP_400_BAD_REQUEST,
            "exact duplicate must 400",
        )

        different_weight = self._create_recipe(packet_weight="4")
        self.assertEqual(
            different_weight.status_code, status.HTTP_201_CREATED, different_weight.content
        )
        self.assertEqual(different_weight.data["packet_weight"], "4.000")

        different_type = self._create_recipe(material_type=self.bag_cover)
        self.assertEqual(different_type.status_code, status.HTTP_201_CREATED)
        self.assertEqual(different_type.data["material_type"]["name"], "bag_outer_cover")

    def test_duplicate_check_includes_a_soft_deleted_recipe(self):
        """A deleted recipe still claims its keys; re-creating it is a 400.

        tests/test_other_material_recipe_api.py::OtherMaterialRecipeApiTest::test_duplicate_check_includes_a_soft_deleted_recipe
        """
        self.login_as(self.seed_admin)
        created = self._create_recipe()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        self.assertEqual(
            self.client.delete(self._delete_url(created.data)).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self._create_recipe().status_code,
            status.HTTP_400_BAD_REQUEST,
            "a soft-deleted recipe must still block the same variant",
        )

    def test_zero_or_negative_bounds_are_rejected(self):
        """tests/test_other_material_recipe_api.py::OtherMaterialRecipeApiTest::test_zero_or_negative_bounds_are_rejected"""
        self.login_as(self.seed_admin)
        for label, body in (
            ("zero packet weight", {"packet_weight": "0", "quantity": "1"}),
            ("negative packet weight", {"packet_weight": "-1", "quantity": "1"}),
            ("zero quantity", {"packet_weight": "2.5", "quantity": "0"}),
            ("negative quantity", {"packet_weight": "2.5", "quantity": "-1"}),
            ("missing fields", {}),
        ):
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.post(
                        RECIPES_URL,
                        {
                            "product": self.product.id,
                            "material_type": self.packet_cover.id,
                            **body,
                        },
                        format="json",
                    ).status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    # -- the no-PATCH rule -----------------------------------------------------

    def test_patch_is_not_allowed_on_any_recipe_url(self):
        """Recipes are never edited in place: PATCH is a 405 on both URLs.

        tests/test_other_material_recipe_api.py::OtherMaterialRecipeApiTest::test_patch_is_not_allowed_on_any_recipe_url
        """
        self.login_as(self.seed_admin)
        created = self._create_recipe()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        for url in (RECIPES_URL, self._delete_url(created.data)):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.patch(url, {"quantity": "9"}, format="json").status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )

    # -- listing --------------------------------------------------------------

    def test_list_is_a_paginated_envelope_of_live_recipes(self):
        """tests/test_other_material_recipe_api.py::OtherMaterialRecipeApiTest::test_list_is_a_paginated_envelope_of_live_recipes"""
        self.login_as(self.seed_admin)
        created = self._create_recipe()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        listing = self.client.get(RECIPES_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["total_count"], 1)
        self.assertEqual(listing.data["results"][0]["public_id"], created.data["public_id"])

    # -- deletion -------------------------------------------------------------

    def test_delete_soft_deletes_and_removes_the_recipe_from_the_api(self):
        """The row is flagged and attributed, drops out of the list, and 404s after.

        tests/test_other_material_recipe_api.py::OtherMaterialRecipeApiTest::test_delete_soft_deletes_and_removes_the_recipe_from_the_api
        """
        self.login_as(self.seed_admin)
        created = self._create_recipe()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        url = self._delete_url(created.data)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)

        recipe = OtherMaterialRecipe.all_objects.get(public_id=created.data["public_id"])
        self.assertTrue(recipe.is_deleted)
        self.assertEqual(recipe.deleted_by_id, self.seed_admin.id)

        listing = self.client.get(RECIPES_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["total_count"], 0)

        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.delete(
                "/api/sales-admin/other-material-recipe/OMR-DOESNOTEXIST"
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
