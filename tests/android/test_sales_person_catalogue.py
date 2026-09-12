"""Android catalogue endpoint: GET /android/api/v1/sales-person-catalogue.

Token-only sales-person endpoint, exercised over the ``AndroidApiTestCase``
baseline (DML-seeded, bearer-token auth). Authentication and role gating are
proven once in ``tests/test_view_contracts.py`` -- what is checked here is the
filtering, the sorting and the payload.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Crop, Product, ProductPackaging, Stage, StageIds
from aggregator.ProductOperations import sync_product_description_items
from authentication.models import SalesPerson
from tests.android.common import AndroidApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
CATALOGUE_URL = "/android/api/v1/sales-person-catalogue"


class AndroidCatalogueApiTest(AndroidApiTestCase):
    """Cover the catalogue's payload, filters and sorts.

    tests/android/test_sales_person_catalogue.py::AndroidCatalogueApiTest
    """

    @classmethod
    def setUpTestData(cls):
        """A sales person, plus one bag per stage across two crops."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        city = City.objects.get(name="Surat")
        cls.sales_person = User.objects.create_user(
            phone_number="9000000101",
            name="Sales One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(
            user=cls.sales_person, city=city, created_by=cls.superuser
        )

        cls.castor = Crop.objects.get(name="Castor")
        cls.bajari = Crop.objects.get(name="Bajari")

        # The DML baseline already ships two products with one packaging each.
        # Everything below is this class's own, so the assertions can name it.
        cls.certificate = cls._product(
            "Zeta Certificate", cls.bajari, StageIds.CERTIFICATE, "100.00"
        )
        cls.breeder = cls._product(
            "Alpha Breeder", cls.castor, StageIds.BREEDER, "300.00"
        )
        cls.foundation = cls._product(
            "Mid Foundation", cls.bajari, StageIds.FOUNDATION, "200.00"
        )

        sync_product_description_items(
            cls.breeder,
            [
                "Yield of best and delicious grains",
                "Ripes in 80 to 85 days",
                "Suitable for all seasons",
            ],
            cls.superuser,
        )

        # One bag each, priced apart so ?sort=price and ?price_* are unambiguous.
        cls.cheap = cls._packaging(cls.certificate, "1.000", 10, "1000.00")
        cls.mid = cls._packaging(cls.foundation, "1.000", 10, "2000.00")
        cls.dear = cls._packaging(cls.breeder, "1.000", 10, "3000.00")

    @classmethod
    def _product(cls, name, crop, stage_id, rate):
        return Product.objects.create(
            name=name,
            crop=crop,
            stage=Stage.by_id(stage_id),
            selling_price=Decimal(rate),
            created_by=cls.superuser,
        )

    @classmethod
    def _packaging(cls, product, packet_weight, packets, price):
        return ProductPackaging.objects.create(
            product=product,
            packet_weight=Decimal(packet_weight),
            packets=packets,
            selling_price=Decimal(price),
            created_by=cls.superuser,
        )

    # -- helpers --------------------------------------------------------------

    def _get(self, query=""):
        self.login_as(self.sales_person)
        response = self.client.get(f"{CATALOGUE_URL}{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def _ids(self, query=""):
        """The packaging public ids on page one, in the order returned."""
        return [row["public_id"] for row in self._get(query)["results"]]

    # -- payload --------------------------------------------------------------

    def test_a_bare_request_returns_the_whole_catalogue_paginated(self):
        data = self._get()
        # Two bags come from the DML baseline, three from this class.
        self.assertEqual(data["total_count"], 5)
        self.assertEqual(data["previous_page_number"], None)
        self.assertIn("available_filters", data)
        self.assertIn("available_sorts", data)

    def test_a_row_carries_the_bag_and_its_product_card(self):
        row = next(
            item
            for item in self._get()["results"]
            if item["public_id"] == self.dear.public_id
        )
        self.assertEqual(row["name"], str(self.dear))
        self.assertEqual(row["packets"], 10)
        self.assertEqual(row["packet_weight"], "1.000")
        self.assertEqual(row["total_weight"], "10.000")
        self.assertEqual(row["selling_price"], "3000.00")
        self.assertEqual(
            row["product"],
            {
                "public_id": self.breeder.public_id,
                "name": "Alpha Breeder",
                "crop": "Castor",
                "stage": {"code": "BREEDER", "name": "Breeder", "sequence": 1},
                "image_url": "",
                "description_items": [
                    "Yield of best and delicious grains",
                    "Ripes in 80 to 85 days",
                    "Suitable for all seasons",
                ],
            },
        )

    def test_a_product_without_bullets_reports_an_empty_list(self):
        row = next(
            item
            for item in self._get()["results"]
            if item["public_id"] == self.cheap.public_id
        )
        self.assertEqual(row["product"]["description_items"], [])

    # -- filters --------------------------------------------------------------

    def test_crop_filter_keeps_only_that_crop(self):
        ids = self._ids(f"?crop={self.castor.id}")
        self.assertIn(self.dear.public_id, ids)
        self.assertNotIn(self.cheap.public_id, ids)

    def test_crop_filter_options_only_offer_crops_that_have_bags(self):
        entry = next(
            item
            for item in self._get()["available_filters"]
            if item["filter"] == "crop"
        )
        self.assertEqual(entry["kind"], "select")
        self.assertEqual(
            sorted(option["label"] for option in entry["options"]),
            ["Bajari", "Castor"],
        )

    def test_product_filter_takes_public_ids(self):
        self.assertEqual(
            self._ids(f"?product={self.breeder.public_id}"), [self.dear.public_id]
        )

    def test_stage_filter_accepts_several_codes(self):
        ids = self._ids("?stage=BREEDER,CERTIFICATE")
        self.assertIn(self.dear.public_id, ids)
        self.assertIn(self.cheap.public_id, ids)
        self.assertNotIn(self.mid.public_id, ids)

    def test_an_unknown_stage_is_rejected(self):
        self.login_as(self.sales_person)
        response = self.client.get(f"{CATALOGUE_URL}?stage=CERTIFIED")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("CERTIFIED", response.data["detail"])

    def test_name_filter_matches_a_substring_case_insensitively(self):
        self.assertEqual(self._ids("?name=alpha"), [self.dear.public_id])

    def test_price_bounds_are_inclusive(self):
        self.assertEqual(
            sorted(self._ids("?price_gte=2000&price_lte=3000")),
            sorted([self.mid.public_id, self.dear.public_id]),
        )

    def test_a_lower_bound_above_the_upper_bound_is_rejected(self):
        self.login_as(self.sales_person)
        response = self.client.get(f"{CATALOGUE_URL}?price_gte=3000&price_lte=1000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_a_non_numeric_price_bound_is_rejected(self):
        self.login_as(self.sales_person)
        response = self.client.get(f"{CATALOGUE_URL}?price_gte=cheap")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filters_are_anded_together(self):
        self.assertEqual(self._ids(f"?crop={self.bajari.id}&stage=FOUNDATION"),
                         [self.mid.public_id])

    # -- sorting --------------------------------------------------------------

    def test_sort_by_price_ascends_and_descends(self):
        mine = [self.cheap.public_id, self.mid.public_id, self.dear.public_id]
        ascending = [pid for pid in self._ids("?sort=price") if pid in mine]
        self.assertEqual(ascending, mine)
        descending = [pid for pid in self._ids("?sort=-price") if pid in mine]
        self.assertEqual(descending, list(reversed(mine)))

    def test_sort_by_stage_runs_breeder_to_certificate(self):
        ids = self._ids(f"?sort=stage&crop={self.castor.id},{self.bajari.id}")
        mine = [self.dear.public_id, self.mid.public_id, self.cheap.public_id]
        self.assertEqual([pid for pid in ids if pid in mine], mine)

    def test_the_default_sort_is_product_name(self):
        names = [row["product"]["name"] for row in self._get()["results"]]
        self.assertEqual(names, sorted(names))

    def test_an_unknown_sort_is_rejected(self):
        self.login_as(self.sales_person)
        response = self.client.get(f"{CATALOGUE_URL}?sort=popularity")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- pagination -----------------------------------------------------------

    def test_page_size_is_honoured(self):
        data = self._get("?page_size=2&sort=price")
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["total_pages"], 3)
        self.assertEqual(data["next_page_number"], 2)

    def test_a_soft_deleted_bag_disappears_from_the_catalogue(self):
        self.dear.is_deleted = True
        self.dear.save(update_fields=["is_deleted", "updated_at"])
        self.assertNotIn(self.dear.public_id, self._ids())
