"""Sales-admin client transfer endpoints.

``client/by-sales-person/<id>``, ``client/transfer-client/`` and ``all-clients/``:
what an admin uses to re-home a departed sales person's clients.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Client, Country, FieldTrip, Order, State
from authentication.models import Admin, SalesPerson
from tests import test_client_api
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

BY_SALES_PERSON_URL = "/api/sales-admin/client/by-sales-person/{id}"
TRANSFER_URL = "/api/sales-admin/client/transfer-client/"
ALL_SALES_PERSON_URL = "/api/sales-admin/all-sales-person/"


class ClientTransferApiTest(WebApiTestCase):
    """Per-sales-person list, transfer and the all-clients directory.

    tests/test_client_transfer_api.py::ClientTransferApiTest
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.leaver_user, cls.leaver = cls._make_sales_person("9000000011", "Leaver")
        cls.heir_user, cls.heir = cls._make_sales_person("9000000012", "Heir")
        cls.admin_user = User.objects.create_user(
            phone_number="9000000013",
            name="Asha Rao",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin_user, created_by=cls.superuser)

    @classmethod
    def _make_sales_person(cls, phone, name):
        user = User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        return user, SalesPerson.objects.create(
            user=user, city=cls.city, created_by=cls.superuser
        )

    def setUp(self):
        super().setUp()
        # Reuse the sibling suite's client builder (GSTs must stay distinct).
        # Imported as a module so pytest does not collect the sibling class here.
        builder = test_client_api.SalesAdminClientApiTest
        builder.country, builder.state, builder.city = self.country, self.state, self.city
        self.first = builder._make_client(
            self, company_name="Alpha", gst_index=0, actor=self.leaver_user
        )
        self.second = builder._make_client(
            self, company_name="Beta", gst_index=1, actor=self.leaver_user
        )
        self.heirs = builder._make_client(
            self, company_name="Gamma", gst_index=2, actor=self.heir_user
        )
        self.login_as(self.admin_user)

    def test_list_by_sales_person_includes_removed_sales_person(self):
        """tests/test_client_transfer_api.py::ClientTransferApiTest::test_list_by_sales_person_includes_removed_sales_person"""
        response = self.client.get(BY_SALES_PERSON_URL.format(id=self.leaver.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {row["public_id"] for row in response.data["results"]},
            {self.first.public_id, self.second.public_id},
        )

        self.leaver.mark_deleted(self.admin_user)
        response = self.client.get(BY_SALES_PERSON_URL.format(id=self.leaver.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_count"], 2)

        response = self.client.get(BY_SALES_PERSON_URL.format(id=999999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_transfer_moves_ownership(self):
        """tests/test_client_transfer_api.py::ClientTransferApiTest::test_transfer_moves_ownership"""
        # A client the target already owns is skipped, not an error.
        response = self.client.post(
            TRANSFER_URL,
            {
                "client_ids": [
                    self.first.public_id,
                    self.second.public_id,
                    self.heirs.public_id,
                ],
                "target_sales_person_id": self.heir.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["transferred_count"], 2)
        self.assertEqual(
            Client.objects.filter(created_by=self.heir_user).count(), 3
        )
        self.assertFalse(Client.objects.filter(created_by=self.leaver_user).exists())

    def test_transfer_rejects_bad_input_and_changes_nothing(self):
        """tests/test_client_transfer_api.py::ClientTransferApiTest::test_transfer_rejects_bad_input_and_changes_nothing"""
        cases = [
            {"client_ids": [], "target_sales_person_id": self.heir.id},
            {
                "client_ids": [self.first.public_id, self.first.public_id],
                "target_sales_person_id": self.heir.id,
            },
            {
                "client_ids": [self.first.public_id, "C-NOPE"],
                "target_sales_person_id": self.heir.id,
            },
        ]
        for body in cases:
            response = self.client.post(TRANSFER_URL, body, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, body)

        # A deleted client is not transferable.
        self.second.mark_deleted(self.admin_user)
        response = self.client.post(
            TRANSFER_URL,
            {
                "client_ids": [self.first.public_id, self.second.public_id],
                "target_sales_person_id": self.heir.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # A removed sales person cannot receive clients.
        self.heir.mark_deleted(self.admin_user)
        response = self.client.post(
            TRANSFER_URL,
            {
                "client_ids": [self.first.public_id],
                "target_sales_person_id": self.heir.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(Client.objects.filter(created_by=self.leaver_user).count(), 1)

    def test_all_sales_person_lists_removed_ones_with_client_counts(self):
        """tests/test_client_transfer_api.py::ClientTransferApiTest::test_all_sales_person_lists_removed_ones_with_client_counts"""
        self.leaver.mark_deleted(self.admin_user)
        response = self.client.get(ALL_SALES_PERSON_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = {row["id"]: row for row in response.data}
        self.assertTrue(rows[self.leaver.id]["is_deleted"])
        self.assertEqual(rows[self.leaver.id]["client_count"], 2)
        self.assertFalse(rows[self.heir.id]["is_deleted"])
        self.assertEqual(rows[self.heir.id]["client_count"], 1)
        self.assertEqual(rows[self.heir.id]["city"], "Surat")

    def test_transfer_leaves_orders_and_other_history_with_the_original_author(self):
        """tests/test_client_transfer_api.py::ClientTransferApiTest::test_transfer_leaves_orders_and_other_history_with_the_original_author"""
        before = {
            (model, obj.pk): obj.created_by_id
            for model in (Order, FieldTrip)
            for obj in model.all_objects.all()
        }
        self.client.post(
            TRANSFER_URL,
            {
                "client_ids": [self.first.public_id, self.second.public_id],
                "target_sales_person_id": self.heir.id,
            },
            format="json",
        )
        after = {
            (model, obj.pk): obj.created_by_id
            for model in (Order, FieldTrip)
            for obj in model.all_objects.all()
        }
        self.assertEqual(before, after)
        self.first.refresh_from_db()
        self.assertEqual(self.first.created_by_id, self.heir_user.pk)
