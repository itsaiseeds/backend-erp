"""``Product.is_usable``: a frozen product can neither be created for nor changed.

Two layers, mirroring the code. The operations layer is where the rule lives
(``ProductOperations.assert_products_usable``, called first by every writer), so
most cases are proven there on ORM objects; the API class then shows each
endpoint reaches it, and covers the switch itself, the payloads and the pickers.

Authentication is owned by ``tests/test_view_contracts.py`` -- not repeated here.
"""

from __future__ import annotations

import datetime
import json
from decimal import Decimal

from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from rest_framework import status

from aggregator import InventoryOperations as inv
from aggregator.ClientOperations import add_client_address, create_client
from aggregator.CustomOrderOperations import (
    create_custom_order,
    delete_custom_order,
    dispatch_custom_order,
)
from aggregator.InwardOperations import create_other_lot, create_raw_lot, update_raw_lot
from aggregator.models import (
    Address,
    City,
    Country,
    InventorySnapshot,
    InwardRawMaterial,
    LooseStockSnapshot,
    OtherMaterialRecipe,
    OtherMaterialType,
    Party,
    PartyType,
    Pincode,
    Product,
    ProductPackaging,
    RawMaterialWaste,
    Stage,
    StageIds,
    State,
    Status,
    StatusIds,
)
from aggregator.OrderOperations import (
    create_order,
    dispatch_order,
    hold_order,
    sync_order_items,
    verify_order,
)
from aggregator.ProductOperations import (
    add_packaging,
    assert_products_usable,
    create_product,
    usable_packagings,
    usable_products,
)
from authentication.models import Admin, SalesPerson
from tests.common import (
    DMLTestCase,
    WebApiTestCase,
    book_raw_material,
    book_raw_material_for_every_product,
)

User = get_user_model()

WEIGHT = Decimal("1.000")


def freeze(product: Product) -> None:
    """Switch ``product`` off the way the API does, without going through it."""
    Product.objects.filter(pk=product.pk).update(is_usable=False)
    product.refresh_from_db()


def unfreeze(product: Product) -> None:
    Product.objects.filter(pk=product.pk).update(is_usable=True)
    product.refresh_from_db()


class ProductUsabilityOperationsTest(DMLTestCase):
    """The guard, every writer that calls it, and the releases that must stay open.

    tests/test_product_usability.py::ProductUsabilityOperationsTest
    """

    # Orders and lots are seeded through raw ORM here and there, like the sibling
    # stock modules, so the ledger-sync assertion does not apply.
    stock_ledger_guard = False

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.sp_user = User.objects.create_user(
            "9400000001", "Sales Person", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.stock_admin = User.objects.create_user(
            "9400000002", "Stock Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        Admin.objects.create(user=cls.stock_admin, created_by=cls.su, can_update_stock_count=True)

        country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.su}
        )
        state = State.objects.create(name="Maharashtra", country=country, created_by=cls.su)
        cls.city = City.objects.create(name="Pune", state=state, created_by=cls.su)
        cls.city2 = City.objects.create(name="Nashik", state=state, created_by=cls.su)
        pincode = Pincode.objects.create(code="411004", city=cls.city, created_by=cls.su)
        SalesPerson.objects.create(user=cls.sp_user, city=cls.city, created_by=cls.su)
        cls.addr = Address.objects.create(
            address_line_1="5 Usable Rd", pincode=pincode, city=cls.city,
            state=state, country=country, created_by=cls.su,
        )
        cls.client_obj = create_client(
            company_name="Usable Traders", gst_number="27AAPFU0939F1ZV", actor=cls.sp_user
        )
        add_client_address(cls.client_obj, cls.addr, cls.sp_user, is_primary=True)

        stage = Stage.by_id(StageIds.BREEDER)
        cls.product = create_product(
            name="Hybrid Jowar", crop="Jowar", stage=stage,
            selling_price=Decimal("150.00"), actor=cls.su,
        )
        cls.product2 = create_product(
            name="Hybrid Bajra", crop="Bajra", stage=stage,
            selling_price=Decimal("150.00"), actor=cls.su,
        )
        cls.pack = add_packaging(cls.product, packet_weight=WEIGHT, packets=40, actor=cls.su)
        cls.pack2 = add_packaging(cls.product2, packet_weight=WEIGHT, packets=40, actor=cls.su)
        cls.party = Party.objects.create(
            name="Usable Party", city_id=1, party_type=PartyType.RAW_MATERIAL, created_by=cls.su
        )
        cls.today = datetime.date.today()
        book_raw_material_for_every_product(actor=cls.su)

    # -- helpers --------------------------------------------------------------

    def _count_all(self, bags: int = 100, *, snapshot_date=None):
        return inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), bags),
            actor=self.stock_admin,
            snapshot_date=snapshot_date,
        )

    def _count_loose(self, packets: int = 100):
        pools = {(p.product, p.packet_weight) for p in ProductPackaging.objects.all()}
        inv.record_loose_stocks(
            counts=dict.fromkeys(pools, packets), actor=self.stock_admin
        )

    def _order(self, *lines):
        return create_order(
            client=self.client_obj,
            delivery_address=self.addr,
            actor=self.sp_user,
            items=[{"product_packaging": p, "quantity": q} for p, q in lines],
        )

    def _refused(self, key: str, call):
        """``call`` raises a ``ValidationError`` carrying a message under ``key``."""
        with self.assertRaises(ValidationError) as ctx:
            call()
        self.assertIn(key, ctx.exception.message_dict)
        return ctx.exception.message_dict[key][0]

    # -- the guard itself -------------------------------------------------------

    def test_the_guard_names_every_frozen_product_and_ignores_usable_ones(self):
        """One message lists all offenders; usable products and None pass silently.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_the_guard_names_every_frozen_product_and_ignores_usable_ones
        """
        assert_products_usable([self.product, self.product2, None])
        assert_products_usable([])

        freeze(self.product)
        message = self._refused(
            "product", lambda: assert_products_usable([self.product, self.product2.pk])
        )
        self.assertEqual(
            message, "Product 'Hybrid Jowar' is not usable, so it cannot be changed."
        )

        freeze(self.product2)
        message = self._refused(
            "x",
            lambda: assert_products_usable(
                [self.product, self.product2],
                field="x",
                action="be ordered",
                subject="this order",
            ),
        )
        self.assertEqual(
            message,
            "Products 'Hybrid Jowar', 'Hybrid Bajra' are not usable, "
            "so this order cannot be ordered.",
        )

    def test_pickers_start_from_usable_rows_only(self):
        """usable_products / usable_packagings leave frozen products out.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_pickers_start_from_usable_rows_only
        """
        self.assertIn(self.product, usable_products())
        self.assertIn(self.pack, usable_packagings())
        freeze(self.product)
        self.assertNotIn(self.product, usable_products())
        self.assertNotIn(self.pack, usable_packagings())
        self.assertIn(self.pack2, usable_packagings())

    # -- inward -------------------------------------------------------------------

    def test_raw_lots_cannot_be_booked_flipped_or_deleted_for_a_frozen_product(self):
        """The existing lot stays exactly as it was; unfreezing re-opens every write.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_raw_lots_cannot_be_booked_flipped_or_deleted_for_a_frozen_product
        """
        lot = create_raw_lot(
            product=self.product, party=self.party, lot_no="L1",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("10"), lab_sampling_date=self.today, actor=self.su,
        )
        freeze(self.product)

        self._refused("product", lambda: create_raw_lot(
            product=self.product, party=self.party, lot_no="L2",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("5"), lab_sampling_date=self.today, actor=self.su,
        ))
        self._refused("status", lambda: update_raw_lot(
            lot,
            {"status": Status.by_id(StatusIds.IN_USE), "effective_date": self.today},
            self.su,
        ))
        self._refused("product", lambda: lot.mark_deleted(self.su))

        lot_in_db = InwardRawMaterial.all_objects.get(pk=lot.pk)
        self.assertEqual(lot_in_db.status_id, StatusIds.LAB_TESTING.value)
        self.assertFalse(lot_in_db.is_deleted)
        self.assertEqual(InwardRawMaterial.objects.filter(lot_no="L2").count(), 0)

        unfreeze(self.product)
        update_raw_lot(
            lot, {"status": Status.by_id(StatusIds.IN_USE), "effective_date": self.today}, self.su
        )

    def test_other_material_lots_and_recipes_are_frozen_with_their_product(self):
        """A lot is reached through its recipe; the recipe itself is frozen too.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_other_material_lots_and_recipes_are_frozen_with_their_product
        """
        recipe = OtherMaterialRecipe.objects.create(
            product=self.product,
            material_type=OtherMaterialType.objects.order_by("id").first(),
            packet_weight=WEIGHT,
            quantity=Decimal("1.000"),
            created_by=self.su,
        )
        lot = create_other_lot(
            party=self.party, recipe=recipe, quantity=Decimal("5"), actor=self.su
        )
        freeze(self.product)

        self._refused("recipe", lambda: create_other_lot(
            party=self.party, recipe=recipe, quantity=Decimal("1"), actor=self.su
        ))
        self._refused("product", lambda: lot.mark_deleted(self.su))
        self._refused("product", lambda: recipe.mark_deleted(self.su))
        self.assertEqual(recipe.__class__.objects.filter(pk=recipe.pk).count(), 1)

    def test_waste_cannot_be_recorded_or_deleted_for_a_frozen_product(self):
        """Waste is a stock write like any other.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_waste_cannot_be_recorded_or_deleted_for_a_frozen_product
        """
        waste = inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("5"), reason="rain", actor=self.su
        )
        freeze(self.product)

        self._refused("product", lambda: inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("1"), reason="more", actor=self.su
        ))
        self._refused("product", lambda: waste.mark_deleted(self.su))
        self.assertEqual(RawMaterialWaste.objects.filter(product=self.product).count(), 1)

    def test_packagings_cannot_be_added_to_a_frozen_product(self):
        """add_packaging goes through the same guard (the API view does too).

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_packagings_cannot_be_added_to_a_frozen_product
        """
        freeze(self.product)
        self._refused("product", lambda: add_packaging(
            self.product, packet_weight=Decimal("2.000"), packets=10, actor=self.su
        ))
        self._refused("product", lambda: self.pack.mark_deleted(self.su))

    # -- counts ---------------------------------------------------------------

    def test_a_frozen_products_count_cannot_be_written_but_is_carried_forward(self):
        """Naming it is refused; a new day carries its figure so nothing moves.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_a_frozen_products_count_cannot_be_written_but_is_carried_forward
        """
        self._count_all(10)
        raw_before = inv.raw_available_kg(self.product)
        freeze(self.product)

        self._refused("counts", lambda: inv.record_stock_counts(
            counts={self.pack: 3}, actor=self.stock_admin
        ))

        tomorrow = self.today + datetime.timedelta(days=1)
        inv.record_stock_counts(
            counts=dict.fromkeys(usable_packagings(), 5),
            actor=self.stock_admin,
            snapshot_date=tomorrow,
            carry_frozen=True,
        )
        carried = InventorySnapshot.objects.get(
            snapshot_date=tomorrow, product_packaging=self.pack
        )
        self.assertEqual(carried.bags, 10)
        # Packed raw material is unchanged: the frozen bags did not read as zero.
        self.assertEqual(inv.raw_available_kg(self.product), raw_before)

        # Without carry_frozen a full upload would have dropped it to zero.
        day_after = tomorrow + datetime.timedelta(days=1)
        inv.record_stock_counts(
            counts=dict.fromkeys(usable_packagings(), 5),
            actor=self.stock_admin,
            snapshot_date=day_after,
        )
        self.assertEqual(inv.on_hand_bags(self.pack, day_after), 0)

    def test_the_count_is_complete_without_a_frozen_products_packagings(self):
        """Nobody can count them, so they must not block the day's completeness.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_the_count_is_complete_without_a_frozen_products_packagings
        """
        day = self.today + datetime.timedelta(days=1)
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.exclude(product=self.product2), 5),
            actor=self.stock_admin,
            snapshot_date=day,
        )
        self.assertFalse(inv.is_stock_count_complete(day))
        freeze(self.product2)
        self.assertTrue(inv.is_stock_count_complete(day))
        self.assertNotIn(self.pack2, list(inv.missing_packagings(day)))

    def test_loose_counts_follow_the_same_rule(self):
        """Refused when named, carried forward on a new day.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_loose_counts_follow_the_same_rule
        """
        self._count_loose(7)
        freeze(self.product)
        self._refused("counts", lambda: inv.record_loose_stocks(
            counts={(self.product, WEIGHT): 1}, actor=self.stock_admin
        ))

        tomorrow = self.today + datetime.timedelta(days=1)
        inv.record_loose_stocks(
            counts={(self.product2, WEIGHT): 3},
            actor=self.stock_admin,
            snapshot_date=tomorrow,
            carry_frozen=True,
        )
        carried = LooseStockSnapshot.objects.get(
            snapshot_date=tomorrow, product=self.product, packet_weight=WEIGHT
        )
        self.assertEqual(carried.packets, 7)

    # -- orders ---------------------------------------------------------------

    def test_a_frozen_product_cannot_be_booked(self):
        """Booking an order for it is refused before anything is written.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_a_frozen_product_cannot_be_booked
        """
        freeze(self.product)
        self._refused("items", lambda: self._order((self.pack, 2)))
        # A usable product beside it does not rescue the order.
        self._refused("items", lambda: self._order((self.pack2, 1), (self.pack, 1)))

    def test_an_open_order_with_a_frozen_product_can_be_released_but_not_advanced(self):
        """Verify and dispatch are refused; hold, which releases stock, still works.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_an_open_order_with_a_frozen_product_can_be_released_but_not_advanced
        """
        self._count_all(100)
        confirmed = self._order((self.pack, 2))
        verify_order(confirmed, self.stock_admin)
        booked = self._order((self.pack, 2))

        freeze(self.product)

        self._refused("status", lambda: verify_order(booked, self.stock_admin))
        self._refused("status", lambda: dispatch_order(
            confirmed,
            actor=self.stock_admin,
            from_city=self.city2,
            driver_name="Ravi",
            driver_number="9876543210",
            vehicle_number="MH12AB1234",
            lot_numbers={self.pack.public_id: "L1"},
        ))
        hold_order(confirmed, actor=self.stock_admin)
        confirmed.refresh_from_db()
        self.assertEqual(confirmed.status.code, "ON_HOLD")
        self.assertEqual(inv.reserved_bags(self.pack), 0)

    def test_an_order_edit_may_lower_or_remove_a_frozen_line_but_not_raise_or_add_it(self):
        """Releases are allowed, growth is not.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_an_order_edit_may_lower_or_remove_a_frozen_line_but_not_raise_or_add_it
        """
        order = self._order((self.pack, 3), (self.pack2, 3))
        freeze(self.product)

        def edit(*lines):
            return sync_order_items(
                order,
                [{"product_packaging": p, "quantity": q} for p, q in lines],
                self.sp_user,
            )

        self._refused("items", lambda: edit((self.pack, 5), (self.pack2, 3)))
        edit((self.pack, 1), (self.pack2, 3))  # lowering is fine
        edit((self.pack2, 3))  # removing is fine
        self._refused("items", lambda: edit((self.pack, 1), (self.pack2, 3)))  # adding back is not

    # -- custom orders ----------------------------------------------------------

    def test_custom_orders_follow_the_same_freeze(self):
        """No new one, no dispatch; withdrawing an open one still releases its packets.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_custom_orders_follow_the_same_freeze
        """
        self._count_loose(100)
        item = {"product": self.product, "packet_weight": WEIGHT, "packets": 5}
        open_order = create_custom_order(
            client=self.client_obj,
            delivery_address=self.addr,
            actor=self.stock_admin,
            items=[item],
        )
        freeze(self.product)

        self._refused("items", lambda: create_custom_order(
            client=self.client_obj,
            delivery_address=self.addr,
            actor=self.stock_admin,
            items=[item],
        ))
        self._refused("status", lambda: dispatch_custom_order(
            open_order,
            actor=self.stock_admin,
            from_city=self.city2,
            driver_name="Ravi",
            driver_number="9876543210",
            vehicle_number="MH12AB1234",
            lot_numbers={(self.product.public_id, WEIGHT): "L1"},
        ))
        delete_custom_order(open_order, self.stock_admin)
        self.assertEqual(inv.reserved_loose_packets(self.product, WEIGHT), 0)

    # -- Django admin -----------------------------------------------------------

    def test_the_admin_makes_a_frozen_products_rows_read_only(self):
        """has_change/has_delete_permission are False for them, True once unfrozen.

        tests/test_product_usability.py::ProductUsabilityOperationsTest::test_the_admin_makes_a_frozen_products_rows_read_only
        """
        request = RequestFactory().get("/")
        request.user = self.su
        model_admin = django_admin.site._registry[ProductPackaging]
        self.assertTrue(model_admin.has_change_permission(request, self.pack))

        freeze(self.product)
        self.assertFalse(model_admin.has_change_permission(request, self.pack))
        self.assertFalse(model_admin.has_delete_permission(request, self.pack))
        # Another product's row is untouched.
        self.assertTrue(model_admin.has_change_permission(request, self.pack2))


class ProductUsabilityApiTest(WebApiTestCase):
    """The switch, the payloads, every endpoint's refusal and the pickers.

    tests/test_product_usability.py::ProductUsabilityApiTest
    """

    stock_ledger_guard = False

    PRODUCTS = "/api/sales-admin/products"
    LOTS = "/api/sales-admin/inward-raw-materials"
    WASTES = "/api/sales-admin/raw-material-wastes"
    PACKAGINGS = "/api/sales-admin/product-packagings"
    RECIPES = "/api/sales-admin/other-material-recipes"
    OTHER_LOTS = "/api/sales-admin/inward-other-materials"
    BAG_COUNT = "/api/sales-admin/update-bag-stock"
    RAW_STOCK = "/api/sales-admin/raw-material-stock"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")
        cls.admin = User.objects.create_user(
            phone_number="7000000011", name="admin", is_verified=True,
            created_by=cls.superuser, verified_by=cls.superuser,
        )
        Admin.objects.create(user=cls.admin, can_update_stock_count=True, created_by=cls.superuser)
        cls.product = Product.objects.get(name="SAI-33")
        cls.party = Party.objects.create(
            name="API Party", city_id=1, party_type=PartyType.RAW_MATERIAL, created_by=cls.admin
        )
        cls.other_party = Party.objects.create(
            name="API Packaging Party", city_id=1, party_type=PartyType.OTHER_MATERIAL,
            created_by=cls.admin,
        )

    def setUp(self):
        super().setUp()
        self.login_as(self.admin)

    # -- helpers ----------------------------------------------------------------

    def _patch(self, **body):
        return self.client.patch(f"{self.PRODUCTS}/{self.product.public_id}", body, format="json")

    def _line(self) -> dict:
        response = self.client.get(self.RAW_STOCK, {"product": self.product.public_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        return response.data["lines"][0]

    def _make_recipe(self) -> OtherMaterialRecipe:
        return OtherMaterialRecipe.objects.create(
            product=self.product,
            material_type=OtherMaterialType.objects.order_by("id").first(),
            packet_weight=WEIGHT,
            quantity=Decimal("1.000"),
            created_by=self.admin,
        )

    # -- the switch ---------------------------------------------------------------

    def test_the_switch_round_trips_and_filters_the_list(self):
        """PATCH flips it; the payload and ?is_usable= filter reflect it.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_the_switch_round_trips_and_filters_the_list
        """
        self.assertTrue(self.client.get(self.PRODUCTS).data[0]["is_usable"])

        off = self._patch(is_usable=False)
        self.assertEqual(off.status_code, status.HTTP_200_OK, off.content)
        self.assertFalse(off.data["is_usable"])

        def names(**params):
            return {row["name"] for row in self.client.get(self.PRODUCTS, params).data}

        self.assertNotIn("SAI-33", names(is_usable="true"))
        self.assertEqual(names(is_usable="false"), {"SAI-33"})
        # The default is dropdown-safe: a frozen product is not offered.
        self.assertNotIn("SAI-33", names())
        # The product management page asks for everything, to re-enable it.
        self.assertIn("SAI-33", names(is_usable="all"))
        self.assertEqual(
            self.client.get(self.PRODUCTS, {"is_usable": "maybe"}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        on = self._patch(is_usable=True)
        self.assertTrue(on.data["is_usable"])

    def test_a_frozen_products_packagings_are_not_offered_by_default(self):
        """The packaging list is a dropdown source too; ?is_usable=all shows them.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_a_frozen_products_packagings_are_not_offered_by_default
        """
        packaging = ProductPackaging.objects.get(product=self.product)

        def listed(**params):
            response = self.client.get(self.PACKAGINGS, params)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
            return {row["public_id"] for row in response.data}

        self.assertIn(packaging.public_id, listed())
        self._patch(is_usable=False)
        self.assertNotIn(packaging.public_id, listed())
        self.assertIn(packaging.public_id, listed(is_usable="all"))
        self.assertEqual(
            self.client.get(self.PACKAGINGS, {"is_usable": "maybe"}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_a_frozen_product_stays_editable_and_new_products_start_usable(self):
        """Its own fields can change; POST ignores is_usable.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_a_frozen_product_stays_editable_and_new_products_start_usable
        """
        self._patch(is_usable=False)
        edited = self._patch(selling_price="130.00")
        self.assertEqual(edited.status_code, status.HTTP_200_OK, edited.content)
        self.assertFalse(edited.data["is_usable"])  # an unrelated edit does not unfreeze it
        self.assertEqual(str(edited.data["selling_price"]), "130.00")

        created = self.client.post(
            self.PRODUCTS,
            {
                "name": "Brand New", "crop": self.product.crop_id,
                "stage": self.product.stage_id, "selling_price": "99.00",
                "is_usable": False,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.content)
        self.assertTrue(created.data["is_usable"])

    # -- refusals ------------------------------------------------------------------

    def test_every_write_endpoint_refuses_a_frozen_product(self):
        """Create, change and delete for inward, waste, packaging, recipe and counts.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_every_write_endpoint_refuses_a_frozen_product
        """
        book_raw_material(self.product, Decimal("500"), actor=self.admin)
        lot = create_raw_lot(
            product=self.product, party=self.party, lot_no="API-1",
            farmer_name="Test Farmer",
            quantity_kg=Decimal("10"), lab_sampling_date=datetime.date.today(), actor=self.admin,
        )
        # In Use, so the admin's only status write -- the revert to Lab Testing -- is a
        # valid transition and the freeze is what refuses it.
        update_raw_lot(
            lot,
            {"status": Status.by_id(StatusIds.IN_USE), "effective_date": datetime.date.today()},
            self.admin,
        )
        waste = inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("2"), reason="x", actor=self.admin
        )
        recipe = self._make_recipe()
        packaging = ProductPackaging.objects.get(product=self.product)

        self._patch(is_usable=False)

        def refused(response):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
            self.assertIn("not usable", str(response.data["detail"]))

        refused(self.client.post(self.LOTS, {
            "product": self.product.public_id, "party": self.party.id,
            "lot_no": "API-2", "farmer_name": "Test Farmer", "quantity_kg": "5",
        }, format="json"))
        refused(self.client.patch(
            f"/api/sales-admin/inward-raw-material/{lot.public_id}", {"status": "Lab Testing"},
            format="json",
        ))
        refused(self.client.delete(f"/api/sales-admin/inward-raw-material/{lot.public_id}"))
        refused(self.client.post(self.WASTES, {
            "product": self.product.public_id, "quantity_kg": "1",
        }, format="json"))
        refused(self.client.delete(f"/api/sales-admin/raw-material-waste/{waste.public_id}"))
        refused(self.client.post(self.PACKAGINGS, {
            "product": self.product.public_id, "packet_weight": "2.000", "packets": 10,
        }, format="json"))
        refused(self.client.patch(
            f"{self.PACKAGINGS}/{packaging.public_id}", {"selling_price": "1.00"}, format="json"
        ))
        refused(self.client.delete(f"{self.PACKAGINGS}/{packaging.public_id}"))
        refused(self.client.post(self.RECIPES, {
            "product": self.product.public_id,
            "material_type": OtherMaterialType.objects.order_by("id").first().id,
            "packet_weight": "2.000", "quantity": "1",
        }, format="json"))
        refused(self.client.delete(f"/api/sales-admin/other-material-recipe/{recipe.public_id}"))
        refused(self.client.post(self.OTHER_LOTS, {
            "party": self.other_party.id, "recipe": recipe.public_id, "quantity": "5",
        }, format="json"))
        counted = self.client.patch(
            self.BAG_COUNT, {"counts": {packaging.public_id: 3}}, format="json"
        )
        self.assertEqual(counted.status_code, status.HTTP_400_BAD_REQUEST, counted.content)
        self.assertIn("unusable", str(counted.data["detail"]))

        # Nothing changed.
        self.assertEqual(InwardRawMaterial.objects.get(pk=lot.pk).status_id,
                         StatusIds.LAB_TESTING.value)
        self.assertTrue(RawMaterialWaste.objects.filter(pk=waste.pk).exists())
        self.assertTrue(ProductPackaging.objects.filter(pk=packaging.pk).exists())
        self.assertTrue(OtherMaterialRecipe.objects.filter(pk=recipe.pk).exists())

    def test_switching_back_on_reopens_every_write(self):
        """The freeze is reversible with no data change.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_switching_back_on_reopens_every_write
        """
        book_raw_material(self.product, Decimal("100"), actor=self.admin)
        body = {"product": self.product.public_id, "quantity_kg": "1"}

        self._patch(is_usable=False)
        self.assertEqual(
            self.client.post(self.WASTES, body, format="json").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self._patch(is_usable=True)
        self.assertEqual(
            self.client.post(self.WASTES, body, format="json").status_code,
            status.HTTP_201_CREATED,
        )

    # -- reads -------------------------------------------------------------------

    def test_the_raw_stock_report_hides_a_frozen_product_and_restores_it_unchanged(self):
        """Frozen: no line at all. Switched back on: the same figures return.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_the_raw_stock_report_hides_a_frozen_product_and_restores_it_unchanged
        """
        book_raw_material(self.product, Decimal("100"), actor=self.admin)
        inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("5"), reason="x", actor=self.admin
        )
        before = self._line()
        self.assertTrue(before["is_usable"])

        self._patch(is_usable=False)
        hidden = self.client.get(self.RAW_STOCK, {"product": self.product.public_id})
        self.assertEqual(hidden.status_code, status.HTTP_200_OK, hidden.content)
        self.assertEqual(hidden.data["lines"], [])

        self._patch(is_usable=True)
        self.assertEqual(self._line(), before)

    def test_a_frozen_products_recipes_are_hidden_from_the_picker_and_the_list(self):
        """Both ``?all=true`` (the booking picker) and the paginated list omit them.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_a_frozen_products_recipes_are_hidden_from_the_picker_and_the_list
        """
        recipe = self._make_recipe()
        self._patch(is_usable=False)

        picker = self.client.get(self.RECIPES, {"all": "true"})
        self.assertEqual(picker.status_code, status.HTTP_200_OK, picker.content)
        self.assertNotIn(recipe.public_id, {r["public_id"] for r in picker.data["results"]})

        listed = self.client.get(self.RECIPES)
        self.assertNotIn(recipe.public_id, {r["public_id"] for r in listed.data["results"]})

        self._patch(is_usable=True)
        listed = self.client.get(self.RECIPES)
        self.assertIn(recipe.public_id, {r["public_id"] for r in listed.data["results"]})

    def test_a_full_bag_count_leaves_a_frozen_packaging_out_and_still_succeeds(self):
        """POST zero-fills only usable packagings; naming a frozen one is a 400.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_a_full_bag_count_leaves_a_frozen_packaging_out_and_still_succeeds
        """
        book_raw_material_for_every_product(actor=self.admin)
        packaging = ProductPackaging.objects.get(product=self.product)
        self._patch(is_usable=False)

        done = self.client.post(self.BAG_COUNT, {"counts": {}}, format="json")
        self.assertEqual(done.status_code, status.HTTP_200_OK, done.content)
        written = {row["packaging"]["public_id"] for row in done.data}
        self.assertNotIn(packaging.public_id, written)

        named = self.client.post(
            self.BAG_COUNT, {"counts": {packaging.public_id: 4}}, format="json"
        )
        self.assertEqual(named.status_code, status.HTTP_400_BAD_REQUEST, named.content)

    def test_a_frozen_product_is_hidden_from_every_material_and_stock_page(self):
        """Lots, waste, recipes, stock pages, get-stock and filter dropdowns all omit it.

        Orders, challans, returns and exports are documents and keep their lines; the
        product page (``?is_usable=all``) still lists it. Switching back on restores
        everything.

        tests/test_product_usability.py::ProductUsabilityApiTest::test_a_frozen_product_is_hidden_from_every_material_and_stock_page
        """
        book_raw_material_for_every_product(actor=self.admin)
        packaging = ProductPackaging.objects.get(product=self.product)
        inv.record_stock_counts(
            counts=dict.fromkeys(ProductPackaging.objects.all(), 5), actor=self.admin
        )
        inv.record_loose_stocks(
            counts={(self.product, packaging.packet_weight): 3}, actor=self.admin
        )
        inv.record_raw_waste(
            product=self.product, quantity_kg=Decimal("2"), reason="x", actor=self.admin
        )
        recipe = self._make_recipe()
        create_other_lot(
            party=self.party, recipe=recipe, quantity=Decimal("4"), actor=self.admin
        )

        pages = {
            "raw lots": self.LOTS,
            "other lots": self.OTHER_LOTS,
            "waste": self.WASTES,
            "recipes": self.RECIPES,
            "raw stock": self.RAW_STOCK,
            "bag stock": "/api/sales-admin/bag-stock",
            "loose stock": "/api/sales-admin/sample-packet-stock",
        }
        ids = (self.product.public_id, packaging.public_id, recipe.public_id)

        def seen_on(url: str) -> bool:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK, (url, response.content))
            body = json.dumps(response.data, default=str)
            return any(public_id in body for public_id in ids)

        for label, url in pages.items():
            with self.subTest(page=label, frozen=False):
                self.assertTrue(seen_on(url), "setup: the usable product should be listed")

        self._patch(is_usable=False)

        for label, url in pages.items():
            with self.subTest(page=label, frozen=True):
                self.assertFalse(seen_on(url), "a frozen product must not appear")
        for public_id in (packaging.public_id, self.product.public_id):
            with self.subTest(get_stock=public_id):
                self.assertEqual(
                    self.client.get(f"/api/sales-admin/get-stock/{public_id}").status_code,
                    status.HTTP_404_NOT_FOUND,
                )
        # Filter dropdowns do not offer it either.
        for url in (self.LOTS, self.WASTES, self.OTHER_LOTS, self.RECIPES):
            with self.subTest(dropdown=url):
                self.assertFalse(seen_on(url + "?page_size=1"))
        # The product page still lists it.
        everything = self.client.get(self.PRODUCTS, {"is_usable": "all"})
        self.assertIn(self.product.public_id, {row["public_id"] for row in everything.data})

        self._patch(is_usable=True)
        for label, url in pages.items():
            with self.subTest(page=label, restored=True):
                self.assertTrue(seen_on(url))
