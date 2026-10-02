"""ORM-backed tests for the godown-manager Android role.

Covers what the godown endpoints *do*; who may call them is owned by
``tests/test_view_contracts.py`` (see ``docs/testing.md``). The inward business
rules themselves are proven by the web inward tests -- here we only show the
Android endpoints reach them (lifecycle, stamping, packed-stock refusals).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.utils import timezone
from rest_framework.authtoken.models import Token

from aggregator import InventoryOperations
from aggregator.models import (
    InwardRawMaterial,
    OtherMaterialRecipe,
    OtherMaterialType,
    Party,
    Product,
    ProductPackaging,
    RawMaterialWaste,
)
from authentication.models import Admin, GodownManager, SalesPerson, User
from tests.android.common import AndroidApiTestCase

BASE = "/android/api/v1/"
LOGIN_URL = BASE + "auth/login"
REAUTH_URL = BASE + "auth/reauthenticate"
TOTP_SECRET = "KRSXG5DSNFXGOIDB"


class GodownManagerApiTest(AndroidApiTestCase):
    """Login payload, inward lots, stock, recipes, look-ups and role revocation.

    tests/android/test_godown.py::GodownManagerApiTest
    """

    # Seeds stock through raw ORM on purpose (dispatches, lots and status flips written
    # directly), so the stock ledger is not expected to follow -- see
    # DMLTestCase.stock_ledger_guard.
    stock_ledger_guard = False


    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number="9999999999")

        def make_user(phone: str, name: str, **extra) -> User:
            return User.objects.create_user(
                phone_number=phone,
                name=name,
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
                **extra,
            )

        cls.manager = GodownManager.objects.create(
            user=make_user(
                "7000000001", "godown manager", totp_secret=TOTP_SECRET, totp_enabled=True
            ),
            created_by=cls.superuser,
        )
        cls.both = make_user("7000000002", "both roles", totp_secret=TOTP_SECRET, totp_enabled=True)
        GodownManager.objects.create(user=cls.both, created_by=cls.superuser)
        SalesPerson.objects.create(user=cls.both, city_id=1, created_by=cls.superuser)
        cls.plain = make_user("7000000003", "plain", totp_secret=TOTP_SECRET, totp_enabled=True)

        cls.product = Product.objects.get(name="SAI-33")
        cls.party = Party.objects.create(name="ABC Traders", city_id=1, created_by=cls.superuser)
        cls.material_type = OtherMaterialType.objects.order_by("id").first()

    def _book_raw(self, **overrides):
        body = {
            "product": self.product.public_id,
            "party": self.party.id,
            "lot_no": "SUP-1",
            "quantity_kg": "40",
            **overrides,
        }
        return self.client.post(BASE + "godown/inward-raw-materials", body, format="json")

    def _on_hand(self, material_type_id: int) -> Decimal:
        stock = self.client.get(BASE + "godown/other-material-stock")
        self.assertEqual(stock.status_code, 200)
        return next(
            (
                Decimal(line["on_hand"])
                for line in stock.data["lines"]
                if line["material_type"]["id"] == material_type_id
            ),
            Decimal("0"),
        )

    @staticmethod
    def _lot_url(public_id: str) -> str:
        return BASE + f"godown/inward-raw-material/{public_id}"

    # -- login payload -----------------------------------------------------------

    def test_login_and_reauthenticate_report_both_role_flags(self):
        """Either role may log in; a user with neither is the generic 400.

        tests/android/test_godown.py::GodownManagerApiTest::test_login_and_reauthenticate_report_both_role_flags
        """
        cases = [
            (self.manager.user, {"is_sales_person": False, "is_godown_manager": True}),
            (self.both, {"is_sales_person": True, "is_godown_manager": True}),
        ]
        for user, flags in cases:
            with self.subTest(user=user.name):
                login = self.client.post(
                    LOGIN_URL,
                    {"phone_number": user.phone_number, "otp": user.totp.now()},
                    format="json",
                )
                self.assertEqual(login.status_code, 200, login.content)
                for key, value in flags.items():
                    self.assertIs(login.data["user"][key], value)

                self.client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
                reauth = self.client.get(REAUTH_URL)
                self.assertEqual(reauth.status_code, 200)
                for key, value in flags.items():
                    self.assertIs(reauth.data["user"][key], value)
                self.clear_auth()

        refused = self.client.post(
            LOGIN_URL,
            {"phone_number": self.plain.phone_number, "otp": self.plain.totp.now()},
            format="json",
        )
        self.assertEqual(refused.status_code, 400)

    # -- inward raw lots ---------------------------------------------------------

    def test_booking_then_in_use_stamps_today_and_feeds_the_stock_endpoint(self):
        """tests/android/test_godown.py::GodownManagerApiTest::test_booking_then_in_use_stamps_today_and_feeds_the_stock_endpoint"""
        self.login_as(self.manager.user)
        booked = self._book_raw()
        self.assertEqual(booked.status_code, 201, booked.content)
        self.assertEqual(booked.data["status"], "Lab Testing")
        self.assertIsNone(booked.data["effective_date"])
        self.assertEqual(
            booked.data["created_by"], {"id": self.manager.user.id, "name": "godown manager"}
        )

        listed = self.client.get(BASE + "godown/inward-raw-materials")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([r["public_id"] for r in listed.data["results"]], [booked.data["public_id"]])

        def incoming() -> str:
            stock = self.client.get(BASE + "godown/raw-material-stock")
            self.assertEqual(stock.status_code, 200)
            line = next(x for x in stock.data["lines"] if x["product"] == self.product.public_id) if stock.data["lines"] else None
            return line["incoming_kg"] if line else "0"

        self.assertEqual(incoming(), "0")
        flipped = self.client.patch(
            self._lot_url(booked.data["public_id"]), {"status": "In Use"}, format="json"
        )
        self.assertEqual(flipped.status_code, 200, flipped.content)
        self.assertEqual(flipped.data["effective_date"], date.today().isoformat())
        self.assertEqual(incoming(), "40.000")

    def test_godown_stock_shows_admin_recorded_waste(self):
        """Waste is admin-only to write, but the godown stock line reports it so
        ``available_kg`` adds up; the waste endpoints themselves stay admin-only.

        tests/android/test_godown.py::GodownManagerApiTest::test_godown_stock_shows_admin_recorded_waste
        """
        self.login_as(self.manager.user)
        booked = self._book_raw()
        self.client.patch(
            self._lot_url(booked.data["public_id"]), {"status": "In Use"}, format="json"
        )
        RawMaterialWaste.objects.create(
            product=self.product,
            quantity_kg=Decimal("5"),
            reason="rain damage",
            created_by=self.superuser,
        )

        stock = self.client.get(BASE + "godown/raw-material-stock")
        self.assertEqual(stock.status_code, 200, stock.content)
        line = next(x for x in stock.data["lines"] if x["product"] == self.product.public_id)
        self.assertEqual(line["incoming_kg"], "40.000")
        self.assertEqual(line["wasted_kg"], "5.000")
        self.assertEqual(line["available_kg"], "35.000")

        # A godown token cannot reach the admin waste endpoints.
        self.assertIn(
            self.client.get("/api/sales-admin/raw-material-wastes").status_code, (401, 403)
        )

    def test_reverting_or_deleting_an_in_use_lot_with_packed_stock_is_400(self):
        """The shared refusals (``assert_raw_lot_removable``) bite from Android.

        tests/android/test_godown.py::GodownManagerApiTest::test_reverting_or_deleting_an_in_use_lot_with_packed_stock_is_400
        """
        self.login_as(self.manager.user)
        booked = self._book_raw()
        url = self._lot_url(booked.data["public_id"])
        self.client.patch(url, {"status": "In Use"}, format="json")
        InventoryOperations.record_stock_count(
            product_packaging=ProductPackaging.objects.get(product=self.product),
            bags=1,
            actor=self.superuser,
        )

        self.assertEqual(
            self.client.patch(url, {"status": "Lab Testing"}, format="json").status_code, 400
        )
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.assertTrue(InwardRawMaterial.objects.filter(public_id=booked.data["public_id"]).exists())

    def test_an_unpacked_lot_can_be_rejected_and_deleted(self):
        """Rejected is reachable (the dashboard's enum omits it) and DELETE corrects a booking.

        tests/android/test_godown.py::GodownManagerApiTest::test_an_unpacked_lot_can_be_rejected_and_deleted
        """
        self.login_as(self.manager.user)
        booked = self._book_raw()
        url = self._lot_url(booked.data["public_id"])
        rejected = self.client.patch(url, {"status": "Rejected"}, format="json")
        self.assertEqual(rejected.status_code, 200, rejected.content)
        self.assertEqual(rejected.data["status"], "Rejected")
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 404)

    # -- other material ----------------------------------------------------------

    def test_other_material_booking_recipes_and_stock(self):
        """Recipes are the picker (``?all=true``), a booking counts today, DELETE removes it.

        tests/android/test_godown.py::GodownManagerApiTest::test_other_material_booking_recipes_and_stock
        """
        recipe = OtherMaterialRecipe.objects.create(
            product=self.product,
            material_type=self.material_type,
            packet_weight="1.000",
            quantity="2.000",
            created_by=self.superuser,
        )
        self.login_as(self.manager.user)
        recipes = self.client.get(BASE + "godown/other-material-recipes", {"all": "true"})
        self.assertEqual(recipes.status_code, 200)
        self.assertEqual([r["public_id"] for r in recipes.data["results"]], [recipe.public_id])

        before = self._on_hand(self.material_type.id)
        booked = self.client.post(
            BASE + "godown/inward-other-materials",
            {"party": self.party.id, "recipe": recipe.public_id, "quantity": "25"},
            format="json",
        )
        self.assertEqual(booked.status_code, 201, booked.content)
        self.assertEqual(booked.data["effective_date"], timezone.localdate().isoformat())
        self.assertEqual(booked.data["created_by"]["id"], self.manager.user.id)
        public_id = booked.data["public_id"]
        item_url = BASE + f"godown/inward-other-material/{public_id}"

        self.assertEqual(self._on_hand(self.material_type.id), before + Decimal("25"))

        self.assertEqual(self.client.patch(item_url, {}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(item_url).status_code, 204)
        listed = self.client.get(BASE + "godown/inward-other-materials")
        self.assertEqual(listed.data["results"], [])

    # -- shared look-ups ---------------------------------------------------------

    def test_lookups_are_flat_lists(self):
        """tests/android/test_godown.py::GodownManagerApiTest::test_lookups_are_flat_lists"""
        self.login_as(self.manager.user)
        parties = self.client.get(BASE + "utilities/parties")
        self.assertEqual(parties.status_code, 200)
        self.assertEqual(
            parties.data,
            [
                {
                    "id": self.party.id,
                    "name": "ABC Traders",
                    "city": {"id": 1, "name": self.party.city.name},
                    "contact_number": self.party.contact_number,
                }
            ],
        )
        types = self.client.get(BASE + "utilities/other-material-types")
        self.assertEqual(types.status_code, 200)
        self.assertEqual(
            {row["id"] for row in types.data},
            set(OtherMaterialType.objects.values_list("id", flat=True)),
        )
        self.assertEqual(set(types.data[0]), {"id", "name", "unit_type"})

    def test_sales_admins_lists_only_opted_in_live_admins_with_name_and_phone_only(self):
        """tests/android/test_godown.py::GodownManagerApiTest::test_sales_admins_lists_only_opted_in_live_admins_with_name_and_phone_only"""

        def make_admin(phone: str, name: str, share: bool) -> Admin:
            user = User.objects.create_user(
                phone_number=phone,
                name=name,
                email=f"{phone}@example.com",
                is_verified=True,
                created_by=self.superuser,
                verified_by=self.superuser,
            )
            return Admin.objects.create(user=user, share_contact=share, created_by=self.superuser)

        make_admin("7100000001", "Shared Admin", True)
        make_admin("7100000002", "Private Admin", False)
        gone = make_admin("7100000003", "Deleted Admin", True)
        gone.mark_deleted(self.superuser)

        self.login_as(self.manager.user)
        response = self.client.get(BASE + "utilities/sales-admins")
        self.assertEqual(response.status_code, 200)
        names = [row["name"] for row in response.data]
        self.assertIn("Shared Admin", names)
        self.assertNotIn("Private Admin", names)
        self.assertNotIn("Deleted Admin", names)
        for row in response.data:
            self.assertEqual(set(row), {"name", "phone_number"})
        shared = next(row for row in response.data if row["name"] == "Shared Admin")
        self.assertEqual(shared["phone_number"], "7100000001")

    # -- role revocation ---------------------------------------------------------

    def test_soft_deleting_a_godown_manager_revokes_the_token(self):
        """tests/android/test_godown.py::GodownManagerApiTest::test_soft_deleting_a_godown_manager_revokes_the_token"""
        token = self.login_as(self.manager.user)
        self.manager.mark_deleted(self.superuser)
        self.assertFalse(Token.objects.filter(key=token.key).exists())
        self.assertEqual(self.client.get(BASE + "godown/raw-material-stock").status_code, 401)
