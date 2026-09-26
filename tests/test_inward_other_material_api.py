"""ORM-backed tests for the inward other-material endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own app admin in ``setUpTestData``. The product (SAI-33), material
type (``packet_outer_cover``) and a recipe fixture are built here.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InwardOperations
from aggregator.models import (
    InwardOtherMaterial,
    OtherMaterialRecipe,
    OtherMaterialType,
    Party,
    Product,
)
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

LOTS_URL = "/api/sales-admin/inward-other-materials"


class InwardOtherMaterialApiTest(WebApiTestCase):
    """Cover the booking lifecycle: defaults, dating later, immutability.

    tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin, a product, a material type, a recipe and a party."""
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
        cls.packet_cover = OtherMaterialType.objects.get(name="packet_outer_cover")
        cls.recipe = OtherMaterialRecipe.objects.create(
            product=cls.product,
            material_type=cls.packet_cover,
            packet_weight=Decimal("2.500"),
            quantity=Decimal("3.000"),
            created_by=cls.seed_admin,
        )
        cls.party = Party.objects.create(
            name="ABC Traders", city_id=1, created_by=cls.seed_admin
        )

    # -- helpers --------------------------------------------------------------

    def _url(self, lot_or_public_id):
        """Return the update/delete URL for a lot (by public id)."""
        public_id = (
            lot_or_public_id
            if isinstance(lot_or_public_id, str)
            else lot_or_public_id["public_id"]
        )
        return f"{LOTS_URL.replace('materials', 'material')}/{public_id}"

    def _create_lot(self, **overrides):
        """POST a lot and return the response (recipe / party / 4 units default)."""
        body = {
            "recipe": self.recipe.public_id,
            "party": self.party.id,
            "quantity": "4",
            **overrides,
        }
        return self.client.post(LOTS_URL, body, format="json")

    # -- creation -------------------------------------------------------------

    def test_a_new_lot_is_dated_today_and_carries_the_recipe_reference(self):
        """Created lots echo the recipe and enter stock on the day they arrive.

        tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest::test_a_new_lot_is_dated_today_and_carries_the_recipe_reference
        """
        self.login_as(self.seed_admin)
        response = self._create_lot()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        lot = response.data

        self.assertTrue(lot["public_id"].startswith("IO-"))
        self.assertEqual(lot["recipe"], {
            "public_id": self.recipe.public_id,
            "product": {"public_id": "P-I34V7RI1JPUH", "name": "SAI-33"},
            "packet_weight": "2.500",
        })
        self.assertEqual(lot["party"], {"id": self.party.id, "name": "ABC Traders"})
        self.assertEqual(lot["quantity"], "4.000")
        self.assertEqual(lot["effective_date"], InwardOperations.today().isoformat())

        created = InwardOtherMaterial.all_objects.get(public_id=lot["public_id"])
        self.assertEqual(created.effective_date, InwardOperations.today())
        self.assertEqual(created.recipe_id, self.recipe.id)
        self.assertEqual(created.created_by_id, self.seed_admin.id)

    def test_recipe_is_addressed_by_public_id_not_pk(self):
        """A ``recipe`` sent as the internal pk (an int) is rejected: a recipe
        is only ever known to the frontend by its ``public_id``.

        tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest::test_recipe_is_addressed_by_public_id_not_pk
        """
        self.login_as(self.seed_admin)
        response = self._create_lot(recipe=self.recipe.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_quantity_bounds_are_checked_and_effective_date_is_not_accepted_on_post(self):
        """Bounds are checked at booking; a posted effective_date is dropped.

        tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest::test_quantity_bounds_are_checked_and_effective_date_is_not_accepted_on_post
        """
        self.login_as(self.seed_admin)
        for label, body in (
            ("zero quantity", {"quantity": "0"}),
            ("negative quantity", {"quantity": "-1"}),
            ("missing quantity", {}),
            ("missing recipe", {"recipe": 999999}),
            ("unknown party", {"party": 999999}),
        ):
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.post(LOTS_URL, body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

        response = self._create_lot(effective_date="2026-09-15")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data["effective_date"], InwardOperations.today().isoformat())

    # -- updating -------------------------------------------------------------

    def test_effective_date_is_stamped_at_booking_and_cannot_be_patched(self):
        """effective_date is not writable; it stays fixed to the booking day.

        tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest::test_effective_date_is_stamped_at_booking_and_cannot_be_patched
        """
        self.login_as(self.seed_admin)
        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = self._url(created.data)

        response = self.client.patch(url, {"effective_date": "2026-09-15"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(
            response.data["effective_date"], InwardOperations.today().isoformat()
        )

        in_db = InwardOtherMaterial.all_objects.get(public_id=created.data["public_id"])
        self.assertEqual(in_db.effective_date, InwardOperations.today())

    def test_booking_fields_are_immutable_on_patch(self):
        """Wrong party / recipe / quantity can't be patched; fixed by delete+rebook.

        tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest::test_booking_fields_are_immutable_on_patch
        """
        self.login_as(self.seed_admin)
        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = self._url(created.data)

        response = self.client.patch(
            url, {"party": 999999, "recipe": 999999, "quantity": "9.999"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["quantity"], "4.000")
        self.assertEqual(response.data["party"], {"id": self.party.id, "name": "ABC Traders"})
        self.assertEqual(response.data["recipe"]["public_id"], self.recipe.public_id)

    # -- listing --------------------------------------------------------------

    def test_list_is_a_paginated_envelope_of_live_lots(self):
        """tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest::test_list_is_a_paginated_envelope_of_live_lots"""
        self.login_as(self.seed_admin)
        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        listing = self.client.get(LOTS_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["total_count"], 1)
        self.assertEqual(listing.data["results"][0]["public_id"], created.data["public_id"])

    def test_product_filter_takes_a_public_id(self):
        """``?product=`` (via the recipe's product) takes the product's public id.

        tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest::test_product_filter_takes_a_public_id
        """
        self.login_as(self.seed_admin)
        self._create_lot()

        response = self.client.get(LOTS_URL, {"product": self.product.public_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["total_count"], 1)

        empty = self.client.get(LOTS_URL, {"product": "P-DOES-NOT-EXIST"})
        self.assertEqual(empty.status_code, status.HTTP_200_OK)
        self.assertEqual(empty.data["total_count"], 0)

    # -- deletion -------------------------------------------------------------

    def test_delete_soft_deletes_and_removes_the_lot_from_the_api(self):
        """The row is flagged and attributed, drops out of the list, and 404s after.

        tests/test_inward_other_material_api.py::InwardOtherMaterialApiTest::test_delete_soft_deletes_and_removes_the_lot_from_the_api
        """
        self.login_as(self.seed_admin)
        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = self._url(created.data)

        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)

        lot = InwardOtherMaterial.all_objects.get(public_id=created.data["public_id"])
        self.assertTrue(lot.is_deleted)
        self.assertEqual(lot.deleted_by_id, self.seed_admin.id)

        listing = self.client.get(LOTS_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["total_count"], 0)

        for verb in ("patch", "delete"):
            with self.subTest(verb=verb):
                self.assertEqual(
                    getattr(self.client, verb)(url, {}, format="json").status_code,
                    status.HTTP_404_NOT_FOUND,
                )

        self.assertEqual(
            self.client.patch(
                "/api/sales-admin/inward-other-material/IO-DOESNOTEXIST",
                {"effective_date": "2026-09-15"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
