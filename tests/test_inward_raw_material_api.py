"""ORM-backed tests for the inward raw-material endpoints (list/create + update/delete).

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone ``9999999999``)
and add their own app admin in ``setUpTestData``. The product (SAI-33) comes from
``dml.sql``; the party is created in this fixture.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations, InwardOperations
from aggregator.models import InwardRawMaterial, Party, Product, ProductPackaging
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

LOTS_URL = "/api/sales-admin/inward-raw-materials"


class InwardRawMaterialApiTest(WebApiTestCase):
    """Cover the booking lifecycle: defaults, dating, two-way flip, deletion.

    tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build an app admin, a seeded product and a party."""
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
        """POST a lot and return the response (defaults: SAI-33 / ABC Traders / 150.5 kg)."""
        body = {
            "product": self.product.public_id,
            "party": self.party.id,
            "quantity_kg": "150.5",
            **overrides,
        }
        return self.client.post(LOTS_URL, body, format="json")

    # -- creation -------------------------------------------------------------

    def test_a_new_lot_starts_lab_testing_undated(self):
        """Created lots default to lab_testing and carry no effective date.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_a_new_lot_starts_lab_testing_undated
        """
        self.login_as(self.seed_admin)
        response = self._create_lot()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        lot = response.data

        self.assertTrue(lot["public_id"].startswith("IR-"))
        self.assertEqual(lot["product"], {"public_id": "P-I34V7RI1JPUH", "name": "SAI-33"})
        self.assertEqual(lot["party"], {"id": self.party.id, "name": "ABC Traders"})
        self.assertEqual(lot["quantity_kg"], "150.500")
        self.assertEqual(lot["status"], "Lab Testing")
        self.assertIsNone(lot["lab_sampling_date"])
        self.assertIsNone(lot["effective_date"])  # never in stock by accident

        created = InwardRawMaterial.all_objects.get(public_id=lot["public_id"])
        self.assertEqual(created.status, "Lab Testing")
        self.assertIsNone(created.effective_date)
        self.assertEqual(created.created_by_id, self.seed_admin.id)

    def test_lab_sampling_date_is_accepted_but_effective_date_is_ignored_on_create(self):
        """Sampling may be recorded at booking; dating is only ever a PATCH.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_lab_sampling_date_is_accepted_but_effective_date_is_ignored_on_create
        """
        self.login_as(self.seed_admin)
        response = self._create_lot(lab_sampling_date="2026-09-10", effective_date="2026-09-15")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data["lab_sampling_date"], "2026-09-10")
        self.assertIsNone(response.data["effective_date"])

    def test_missing_or_invalid_create_fields_are_400(self):
        """tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_missing_or_invalid_create_fields_are_400"""
        self.login_as(self.seed_admin)
        cases = [
            ("missing product", {"party": self.party.id, "quantity_kg": "10"}),
            ("missing party", {"product": self.product.public_id, "quantity_kg": "10"}),
            (
                "missing quantity",
                {"product": self.product.public_id, "party": self.party.id},
            ),
            ("negative quantity", {"quantity_kg": "-1"}),
            ("unknown product", {"product": "P-UNKNOWN0000", "quantity_kg": "10"}),
            ("unknown party", {"party": 999999, "quantity_kg": "10"}),
        ]
        for label, body in cases:
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.post(LOTS_URL, body, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    # -- the lifecycle --------------------------------------------------------

    def test_flipping_to_in_use_stamps_today_and_reverting_clears_it(self):
        """in_use stamps today; reverting to lab_testing clears the date.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_flipping_to_in_use_stamps_today_and_reverting_clears_it
        """
        self.login_as(self.seed_admin)
        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = self._url(created.data)

        # No date is ever typed -- the flip stamps today.
        flipped = self.client.patch(url, {"status": "In Use"}, format="json")
        self.assertEqual(flipped.status_code, status.HTTP_200_OK, flipped.content)
        self.assertEqual(flipped.data["status"], "In Use")
        self.assertEqual(flipped.data["effective_date"], InwardOperations.today().isoformat())

        in_db = InwardRawMaterial.all_objects.get(public_id=created.data["public_id"])
        self.assertEqual(in_db.effective_date, InwardOperations.today())

        # Reverting is allowed and clears the date, dropping the lot out of stock.
        reverted = self.client.patch(url, {"status": "Lab Testing"}, format="json")
        self.assertEqual(reverted.status_code, status.HTTP_200_OK, reverted.content)
        self.assertEqual(reverted.data["status"], "Lab Testing")
        self.assertIsNone(reverted.data["effective_date"])

        in_db.refresh_from_db()
        self.assertEqual(in_db.status, "Lab Testing")
        self.assertIsNone(in_db.effective_date)

        # And the lot can be flipped into stock again later, re-stamped fresh.
        reflipped = self.client.patch(url, {"status": "In Use"}, format="json")
        self.assertEqual(reflipped.status_code, status.HTTP_200_OK, reflipped.content)
        self.assertEqual(reflipped.data["status"], "In Use")
        self.assertEqual(reflipped.data["effective_date"], InwardOperations.today().isoformat())

        # The old snake_case codes are no longer accepted.
        for old_code in ("in_use", "lab_testing"):
            with self.subTest(old_code=old_code):
                self.assertEqual(
                    self.client.patch(url, {"status": old_code}, format="json").status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    def test_reverting_a_lot_with_packed_stock_is_rejected(self):
        """A lot cannot revert out of in_use once its kilograms are packed
        into a bag count -- that would strand bags with no raw material.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_reverting_a_lot_with_packed_stock_is_rejected
        """
        self.login_as(self.seed_admin)
        created = self._create_lot(quantity_kg="40")  # SAI-33's bag is 1kg x 40 = 40kg
        url = self._url(created.data)
        self.client.patch(url, {"status": "In Use"}, format="json")

        pack = ProductPackaging.objects.get(product=self.product)
        InventoryOperations.record_stock_count(
            product_packaging=pack, bags=1, actor=self.seed_admin
        )

        reverted = self.client.patch(url, {"status": "Lab Testing"}, format="json")
        self.assertEqual(reverted.status_code, status.HTTP_400_BAD_REQUEST, reverted.content)

        in_db = InwardRawMaterial.all_objects.get(public_id=created.data["public_id"])
        self.assertEqual(in_db.status, "In Use")

    def test_deleting_a_lot_with_packed_stock_is_rejected(self):
        """A lot cannot be deleted once its kilograms are packed into a bag
        count -- for the same reason a revert is refused.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_deleting_a_lot_with_packed_stock_is_rejected
        """
        self.login_as(self.seed_admin)
        created = self._create_lot(quantity_kg="40")
        url = self._url(created.data)
        self.client.patch(url, {"status": "In Use"}, format="json")

        pack = ProductPackaging.objects.get(product=self.product)
        InventoryOperations.record_stock_count(
            product_packaging=pack, bags=1, actor=self.seed_admin
        )

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertTrue(
            InwardRawMaterial.objects.filter(public_id=created.data["public_id"]).exists()
        )

    def test_the_stamped_date_is_not_an_input_field_while_in_use(self):
        """effective_date is never writable; only a revert clears it.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_the_stamped_date_is_not_an_input_field_while_in_use
        """
        self.login_as(self.seed_admin)
        created = self._create_lot()
        url = self._url(created.data)
        flipped = self.client.patch(url, {"status": "In Use"}, format="json")
        self.assertEqual(flipped.status_code, status.HTTP_200_OK, flipped.content)
        stamped = flipped.data["effective_date"]

        # effective_date is not an input field: attempts to clear or move it are
        # dropped, so while the lot stays in_use the stamped date never changes.
        for label, body in (
            ("clear it", {"effective_date": None}),
            ("move it", {"effective_date": "2026-09-16"}),
        ):
            with self.subTest(case=label):
                response = self.client.patch(url, body, format="json")
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
                self.assertEqual(response.data["effective_date"], stamped)

    def test_product_party_and_quantity_are_immutable(self):
        """Sneaking a new booking into a PATCH changes nothing.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_product_party_and_quantity_are_immutable
        """
        self.login_as(self.seed_admin)
        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = self._url(created.data)

        response = self.client.patch(
            url,
            {
                "product": 999999,
                "party": 999999,
                "quantity_kg": "0.001",
                "lab_sampling_date": "2026-09-12",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["quantity_kg"], "150.500")
        self.assertEqual(response.data["product"]["public_id"], "P-I34V7RI1JPUH")
        self.assertEqual(response.data["party"]["id"], self.party.id)
        self.assertEqual(response.data["lab_sampling_date"], "2026-09-12")

    # -- listing --------------------------------------------------------------

    def test_list_is_a_paginated_envelope_of_live_lots(self):
        """tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_list_is_a_paginated_envelope_of_live_lots"""
        self.login_as(self.seed_admin)
        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        listing = self.client.get(LOTS_URL)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["total_count"], 1)
        self.assertEqual(listing.data["results"][0]["public_id"], created.data["public_id"])

    def test_product_is_addressed_by_public_id_not_pk(self):
        """Create and the ``?product=`` filter both take the product's public id.

        A ``product`` field sent as the internal pk (an int) is rejected: the
        product is only ever known to the frontend by its ``public_id``.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_product_is_addressed_by_public_id_not_pk
        """
        self.login_as(self.seed_admin)

        by_pk = self.client.post(
            LOTS_URL,
            {"product": self.product.id, "party": self.party.id, "quantity_kg": "10"},
            format="json",
        )
        self.assertEqual(by_pk.status_code, status.HTTP_400_BAD_REQUEST, by_pk.content)

        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)

        filtered = self.client.get(LOTS_URL, {"product": self.product.public_id})
        self.assertEqual(filtered.status_code, status.HTTP_200_OK, filtered.content)
        self.assertEqual(filtered.data["total_count"], 1)

        empty = self.client.get(LOTS_URL, {"product": "P-DOES-NOT-EXIST"})
        self.assertEqual(empty.status_code, status.HTTP_200_OK)
        self.assertEqual(empty.data["total_count"], 0)

    # -- deletion -------------------------------------------------------------

    def test_delete_soft_deletes_and_removes_the_lot_from_the_api(self):
        """The row is flagged and attributed, drops out of the list, and 404s after.

        tests/test_inward_raw_material_api.py::InwardRawMaterialApiTest::test_delete_soft_deletes_and_removes_the_lot_from_the_api
        """
        self.login_as(self.seed_admin)
        created = self._create_lot()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        url = self._url(created.data)

        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)

        lot = InwardRawMaterial.all_objects.get(public_id=created.data["public_id"])
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
                "/api/sales-admin/inward-raw-material/IR-DOESNOTEXIST",
                {"status": "In Use"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
