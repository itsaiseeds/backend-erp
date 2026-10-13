"""``POST /api/sales-admin/transfer-product``: raw material moved between two products.

What is proven here is the transfer itself: which lots shrink and which are
booked, what is refused and why, and that the stock ledger follows. Who may call
it is proven once in ``tests/test_view_contracts.py``; the ledger drift guard of
``DMLTestCase`` also runs after every test below.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import create_client_with_details
from aggregator.models import (
    City,
    Country,
    Crop,
    InwardRawMaterial,
    Product,
    ProductPackaging,
    Stage,
    StageIds,
    State,
    StockEvent,
    StockEventDetail,
)
from aggregator.OrderOperations import create_order
from authentication.models import Admin, SalesPerson
from tests.common import WebApiTestCase, book_raw_material, book_raw_material_for_every_product

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
URL = "/api/sales-admin/transfer-product"


class TransferProductApiTest(WebApiTestCase):
    """tests/test_transfer_product_api.py::TransferProductApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        country = Country.objects.get(name="India")
        state = State.objects.get(name="Gujarat", country=country)
        cls.city = City.objects.get(name="Surat", state=state)

        cls.admin_user = cls._user("9000000901", "Transfer Admin")
        Admin.objects.create(
            user=cls.admin_user, created_by=cls.superuser, can_update_stock_count=True
        )
        cls.limited_admin = cls._user("9000000902", "Limited Admin")
        Admin.objects.create(
            user=cls.limited_admin, created_by=cls.superuser, can_update_stock_count=False
        )
        cls.sales_user = cls._user("9000000903", "Transfer Sales")
        SalesPerson.objects.create(user=cls.sales_user, city=cls.city, created_by=cls.superuser)

        cls.crop = Crop.objects.create(name="Transfer Wheat", created_by=cls.superuser)
        cls.other_crop = Crop.objects.create(name="Transfer Rice", created_by=cls.superuser)
        cls.source = cls._product("tx-33", cls.crop)
        cls.target = cls._product("tx-balwan", cls.crop)

        cls.client_row = create_client_with_details(
            company_name="Transfer Seeds",
            company_phone="9876543210",
            gst_number="",
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "line_2": "",
                    "pincode": "395007",
                    "city": cls.city,
                    "state": state,
                    "country": country,
                    "label": "Warehouse",
                    "is_primary": True,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": "Transfer Transport"}],
            actor=cls.sales_user,
        )

    @classmethod
    def _user(cls, phone, name):
        return User.objects.create_user(
            phone_number=phone,
            name=name,
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )

    @classmethod
    def _product(cls, name, crop):
        return Product.objects.create(
            name=name,
            crop=crop,
            stage=Stage.by_id(StageIds.CERTIFIED),
            selling_price=Decimal("100.00"),
            created_by=cls.superuser,
        )

    def setUp(self):
        super().setUp()
        self.login_as(self.admin_user)

    # -- helpers --------------------------------------------------------------

    def _lots(self, product, *quantities):
        return [book_raw_material(product, Decimal(q), actor=self.admin_user) for q in quantities]

    def _transfer(self, quantity="55", source=None, target=None):
        return self.client.post(
            URL,
            {
                "source_product": (source or self.source).public_id,
                "target_product": (target or self.target).public_id,
                "quantity_kg": quantity,
            },
            format="json",
        )

    def _refused(self, response, fragment):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(fragment, str(response.data))

    def _live_lots(self, product):
        return list(
            InwardRawMaterial.objects.filter(product=product).order_by("effective_date", "pk")
        )

    # -- the move -------------------------------------------------------------

    def test_partial_transfer_leaves_the_rest_with_the_source(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_partial_transfer_leaves_the_rest_with_the_source"""
        self._lots(self.source, "100")

        response = self._transfer("55")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["transferred_kg"], "55.000")
        self.assertEqual(response.data["source"]["name"], "tx-33")
        self.assertEqual(response.data["source"]["available_kg"], "45.000")
        self.assertEqual(response.data["target"]["name"], "tx-balwan")
        self.assertEqual(response.data["target"]["available_kg"], "55.000")
        [booked] = response.data["target_lots"]
        self.assertEqual(booked["product"]["public_id"], self.target.public_id)
        self.assertEqual(booked["quantity_kg"], "55.000")
        self.assertEqual(booked["status"], "In Use")
        self.assertEqual(booked["lot_no"], "TEST-LOT")
        self.assertEqual(booked["farmer_name"], "Test Farmer (transferred from tx-33)")
        self.assertEqual([lot.quantity_kg for lot in self._live_lots(self.source)], [Decimal("45")])
        self.assertEqual(inv.raw_available_kg(self.source), Decimal("45"))
        self.assertEqual(inv.raw_available_kg(self.target), Decimal("55"))

    def test_transfer_of_everything_empties_the_source(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_transfer_of_everything_empties_the_source"""
        self._lots(self.source, "100")

        response = self._transfer("100")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["source"]["available_kg"], "0.000")
        self.assertEqual(self._live_lots(self.source), [])
        self.assertEqual(inv.raw_available_kg(self.target), Decimal("100"))

    def test_transfer_draws_oldest_lots_first_and_retires_emptied_ones(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_transfer_draws_oldest_lots_first_and_retires_emptied_ones"""
        first, second = self._lots(self.source, "60", "40")

        response = self._transfer("70")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [lot["quantity_kg"] for lot in response.data["target_lots"]], ["60.000", "10.000"]
        )
        self.assertFalse(InwardRawMaterial.objects.filter(pk=first.pk).exists())
        retired = InwardRawMaterial.all_objects.get(pk=first.pk)
        self.assertTrue(retired.is_deleted)
        self.assertEqual(retired.deleted_by, self.admin_user)
        second.refresh_from_db()
        self.assertEqual(second.quantity_kg, Decimal("30"))
        self.assertEqual(inv.raw_available_kg(self.source), Decimal("30"))

    def test_transfer_is_one_ledger_event_per_product(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_transfer_is_one_ledger_event_per_product"""
        self._lots(self.source, "100")
        before = StockEvent.objects.order_by("-id").values_list("id", flat=True).first() or 0

        self._transfer("55")

        events = StockEvent.objects.filter(id__gt=before).order_by("product_id")
        by_product = {event.product_id: event for event in events}
        self.assertEqual(set(by_product), {self.source.id, self.target.id})
        for event in events:
            self.assertEqual(event.detail, StockEventDetail.RAW_LOT_TRANSFERRED)
            self.assertEqual(event.actor_id, self.admin_user.id)
        [source_line] = by_product[self.source.id].lines.all()
        [target_line] = by_product[self.target.id].lines.all()
        self.assertEqual(source_line.d_incoming, Decimal("-55"))
        self.assertEqual(target_line.d_incoming, Decimal("55"))

    def test_a_fully_transferred_source_leaves_the_stock_and_inward_lists(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_a_fully_transferred_source_leaves_the_stock_and_inward_lists"""
        [lot] = self._lots(self.source, "100")
        before = StockEvent.objects.order_by("-id").values_list("id", flat=True).first() or 0

        self.assertEqual(self._transfer("100").status_code, status.HTTP_200_OK)

        stock = self.client.get("/api/sales-admin/raw-material-stock").data["lines"]
        listed = {line["product"]: line["available_kg"] for line in stock}
        self.assertNotIn(self.source.public_id, listed, "an emptied source is not listed")
        self.assertEqual(listed[self.target.public_id], "100.000")
        inward = self.client.get(
            "/api/sales-admin/inward-raw-materials", {"product": self.source.public_id}
        ).data
        self.assertEqual(inward["results"], [], "its emptied lot is retired")
        retired = InwardRawMaterial.all_objects.get(pk=lot.pk)
        self.assertTrue(retired.is_deleted)
        self.assertEqual(retired.quantity_kg, Decimal("0"))
        # The ledger carries the whole move: -100 on the source, +100 on the target.
        lines = {
            event.product_id: event.lines.get()
            for event in StockEvent.objects.filter(id__gt=before)
        }
        self.assertEqual(lines[self.source.id].d_incoming, Decimal("-100"))
        self.assertEqual(lines[self.target.id].d_incoming, Decimal("100"))

    # -- what is refused ------------------------------------------------------

    def test_more_than_the_source_has_is_refused(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_more_than_the_source_has_is_refused"""
        self._lots(self.source, "100")

        response = self._transfer("100.001")

        self._refused(response, "Not enough raw material in 'tx-33'")
        self.assertEqual(inv.raw_available_kg(self.source), Decimal("100"))
        self.assertEqual(inv.raw_available_kg(self.target), Decimal("0"))

    def test_material_still_in_lab_testing_is_not_movable(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_material_still_in_lab_testing_is_not_movable"""
        from datetime import date

        from aggregator import InwardOperations
        from aggregator.models import Party, PartyType

        party = Party.objects.create(
            name="Lab Party", city_id=1, party_type=PartyType.RAW_MATERIAL,
            created_by=self.admin_user,
        )
        InwardOperations.create_raw_lot(
            product=self.source, party=party, lot_no="L-1", farmer_name="Farmer",
            quantity_kg=Decimal("50"), lab_sampling_date=date.today(), actor=self.admin_user,
        )

        response = self._transfer("10")

        self._refused(response, "Not enough raw material")

    def test_the_products_must_share_a_crop(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_the_products_must_share_a_crop"""
        rice = self._product("tx-rice", self.other_crop)
        self._lots(self.source, "100")

        response = self._transfer("10", target=rice)

        self._refused(response, "within one crop")
        self.assertEqual(inv.raw_available_kg(self.source), Decimal("100"))

    def test_a_product_cannot_be_transferred_to_itself(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_a_product_cannot_be_transferred_to_itself"""
        self._lots(self.source, "100")

        response = self._transfer("10", target=self.source)

        self._refused(response, "must be different")

    def test_a_frozen_product_takes_no_part(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_a_frozen_product_takes_no_part"""
        self._lots(self.source, "100")
        Product.objects.filter(pk=self.target.pk).update(is_usable=False)

        response = self._transfer("10")

        self._refused(response, "not usable")

    def test_bags_in_stock_block_the_transfer(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_bags_in_stock_block_the_transfer"""
        bag = ProductPackaging.objects.create(
            product=self.source,
            packet_weight=Decimal("1.000"),
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=self.superuser,
        )
        self._lots(self.source, "100")
        book_raw_material_for_every_product(actor=self.superuser)
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), 0) | {bag: 1},
            actor=self.admin_user,
        )

        response = self._transfer("10")

        self._refused(response, "1 bag(s) in stock")

    def test_an_open_order_blocks_the_transfer(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_an_open_order_blocks_the_transfer"""
        bag = ProductPackaging.objects.create(
            product=self.source,
            packet_weight=Decimal("1.000"),
            packets=10,
            selling_price=Decimal("1000.00"),
            created_by=self.superuser,
        )
        self._lots(self.source, "100")
        create_order(
            client=self.client_row,
            delivery_address=self.client_row.client_addresses.first().address,
            actor=self.sales_user,
            items=[{"product_packaging": bag, "quantity": 2}],
        )

        response = self._transfer("10")

        self._refused(response, "open orders")
        self.assertEqual(inv.raw_available_kg(self.source), Decimal("100"))

    def test_validation_of_the_request(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_validation_of_the_request"""
        self._lots(self.source, "100")
        cases = {
            "unknown source": self.client.post(
                URL,
                {"source_product": "P-NOPE", "target_product": self.target.public_id,
                 "quantity_kg": "10"},
                format="json",
            ),
            "unknown target": self.client.post(
                URL,
                {"source_product": self.source.public_id, "target_product": "P-NOPE",
                 "quantity_kg": "10"},
                format="json",
            ),
            "a name instead of an id": self.client.post(
                URL,
                {"source_product": "tx-33", "target_product": self.target.public_id,
                 "quantity_kg": "10"},
                format="json",
            ),
            "zero kg": self._transfer("0"),
            "negative kg": self._transfer("-5"),
            "four decimals": self._transfer("1.0001"),
            "missing everything": self.client.post(URL, {}, format="json"),
        }
        for label, response in cases.items():
            with self.subTest(case=label):
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_two_products_with_one_name_are_told_apart_by_id(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_two_products_with_one_name_are_told_apart_by_id"""
        twin = self._product("tx-33", self.other_crop)
        self._lots(self.source, "100")

        response = self._transfer("10", source=self.source)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["source"]["public_id"], self.source.public_id)
        self.assertNotEqual(self.source.public_id, twin.public_id)
        self.assertEqual(inv.raw_available_kg(twin), Decimal("0"))

    # -- who may ----------------------------------------------------------------

    def test_an_admin_who_may_not_change_inward_material_is_refused(self):
        """tests/test_transfer_product_api.py::TransferProductApiTest::test_an_admin_who_may_not_change_inward_material_is_refused"""
        self._lots(self.source, "100")
        self.login_as(self.limited_admin)

        response = self._transfer("10")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        self.assertEqual(inv.raw_available_kg(self.source), Decimal("100"))
