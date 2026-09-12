"""ORM-backed tests for the admin / salesperson update and delete endpoints.

These use the ``WebApiTestCase`` baseline (DML-seeded, superuser phone
``9999999999``) and add their own geography + profiles in ``setUpTestData``.
Update flows are exercised over the test :class:`~rest_framework.test.APIClient`
with a logged-in session, since these are session-only web endpoints.

Who may call these endpoints is *not* retested here: ``UpdateAdminView`` is
``superuser_required`` and ``UpdateSalesPersonView`` is ``admin_required``,
both pinned in ``tests/test_view_contracts.py``. What is tested here is the
behaviour those endpoints add on top -- which fields are writable, which
payloads are refused, and what a soft delete leaves behind.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status

from aggregator.models import City, Country, State
from authentication.models import Admin, SalesPerson
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"

ADMIN_URL = "/api/sales-admin/admins/{id}"
SALESPERSON_URL = "/api/sales-admin/sales-people/{id}"


class UserUpdateTest(WebApiTestCase):
    """Cover field updates, payload shape and soft delete for admin/salesperson.

    tests/test_user_update.py::UserUpdateTest
    """

    @classmethod
    def setUpTestData(cls):
        """Build the geography tree, an app admin and a salesperson."""
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.superuser_admin = Admin.objects.create(
            user=cls.superuser, can_update_stock_count=True, created_by=cls.superuser
        )
        cls.country, _ = Country.objects.get_or_create(
            name="India", defaults={"iso_code": "IN", "created_by": cls.superuser}
        )
        cls.state = State.objects.create(
            name="Maharashtra", code="MH", country=cls.country, created_by=cls.superuser
        )
        cls.city = City.objects.create(name="Pune", state=cls.state, created_by=cls.superuser)
        cls.city_2 = City.objects.create(name="Mumbai", state=cls.state, created_by=cls.superuser)

        cls.seed_admin = User.objects.create_user(
            phone_number="7777777777",
            name="seed admin",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        cls.admin = Admin.objects.create(
            user=cls.seed_admin, can_update_stock_count=True, created_by=cls.superuser
        )

        cls.salesperson = SalesPerson.objects.create(
            user=User.objects.create_user(
                phone_number="5555555555",
                name="seed salesperson",
                is_verified=True,
                created_by=cls.superuser,
                verified_by=cls.superuser,
            ),
            city=cls.city,
            created_by=cls.superuser,
        )

    # -- helpers --------------------------------------------------------------

    def _patch_admin(self, body, actor=None):
        self.login_as(actor or self.superuser)
        return self.client.patch(ADMIN_URL.format(id=self.admin.id), body, format="json")

    def _patch_salesperson(self, body, actor=None):
        self.login_as(actor or self.seed_admin)
        return self.client.patch(
            SALESPERSON_URL.format(id=self.salesperson.id), body, format="json"
        )

    # -- admin: writable fields ----------------------------------------------

    def test_every_writable_admin_field_round_trips(self):
        """Each field is patchable on its own, echoed back, and persisted.

        tests/test_user_update.py::UserUpdateTest::test_every_writable_admin_field_round_trips
        """
        cases = [
            # (payload field, sent value, response value, row holding it, attribute)
            ("name", "Updated Admin", "Updated Admin", "user", "name"),
            ("email", "updated@example.com", "updated@example.com", "user", "email"),
            ("phone_number", "9999999998", "9999999998", "user", "phone_number"),
            ("can_update_stock_count", False, False, "profile", "can_update_stock_count"),
        ]
        for field, sent, expected, row, attribute in cases:
            with self.subTest(field=field):
                response = self._patch_admin({field: sent})
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
                self.assertEqual(response.data[field], expected)
                obj = self.seed_admin if row == "user" else self.admin
                obj.refresh_from_db()
                self.assertEqual(getattr(obj, attribute), expected)

    def test_an_admin_patch_touches_only_the_fields_it_names(self):
        """A multi-field body updates all of them; a partial body leaves the rest alone.

        tests/test_user_update.py::UserUpdateTest::test_an_admin_patch_touches_only_the_fields_it_names
        """
        response = self._patch_admin(
            {"name": "Bulk Updated", "email": "bulk@example.com", "can_update_stock_count": False}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.seed_admin.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual(self.seed_admin.name, "Bulk Updated")
        self.assertEqual(self.seed_admin.email, "bulk@example.com")
        self.assertFalse(self.admin.can_update_stock_count)

        # A body naming only `name` must not disturb email or the stock flag.
        self._patch_admin({"name": "Only Name"})
        self.seed_admin.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual(self.seed_admin.name, "Only Name")
        self.assertEqual(self.seed_admin.email, "bulk@example.com")
        self.assertFalse(self.admin.can_update_stock_count)

        # An empty body is a no-op, not an error.
        response = self._patch_admin({})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["name"], "Only Name")

    def test_invalid_admin_payloads_are_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_invalid_admin_payloads_are_rejected"""
        cases = [
            ("invalid email", {"email": "not-an-email"}),
            ("malformed phone", {"phone_number": "12345"}),
            ("phone already taken", {"phone_number": "5555555555"}),
        ]
        for label, body in cases:
            with self.subTest(case=label):
                self.assertEqual(
                    self._patch_admin(body).status_code, status.HTTP_400_BAD_REQUEST
                )

    def test_resending_an_admins_own_phone_number_is_allowed(self):
        """Regression: the uniqueness check used to match the row being edited itself,
        so an unchanged ``phone_number`` in the payload 400'd.

        tests/test_user_update.py::UserUpdateTest::test_resending_an_admins_own_phone_number_is_allowed
        """
        response = self._patch_admin(
            {"phone_number": self.seed_admin.phone_number, "name": "Same Phone"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.seed_admin.refresh_from_db()
        self.assertEqual(self.seed_admin.name, "Same Phone")

    def test_admin_payload_shape(self):
        """tests/test_user_update.py::UserUpdateTest::test_admin_payload_shape"""
        admin = self._patch_admin({"name": "Payload Check"}).data
        self.assertEqual(admin["role"], "admin")
        self.assertEqual(admin["id"], self.admin.id)
        for key in ("created_by", "created_at", "can_update_stock_count"):
            self.assertIn(key, admin)
        for key in ("user_id", "city", "address", "is_deleted", "deleted_by", "totp"):
            self.assertNotIn(key, admin)

    # -- salesperson: writable fields ----------------------------------------

    def test_every_writable_salesperson_field_round_trips(self):
        """tests/test_user_update.py::UserUpdateTest::test_every_writable_salesperson_field_round_trips"""
        cases = [
            ("name", "Updated Person", "Updated Person", "user", "name"),
            ("email", "person@example.com", "person@example.com", "user", "email"),
            ("phone_number", "9999999990", "9999999990", "user", "phone_number"),
        ]
        for field, sent, expected, _row, attribute in cases:
            with self.subTest(field=field):
                response = self._patch_salesperson({field: sent})
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
                self.assertEqual(response.data[field], expected)
                self.salesperson.user.refresh_from_db()
                self.assertEqual(getattr(self.salesperson.user, attribute), expected)

        # `city` is on the profile and serialises as a nested object, so it does
        # not fit the flat table above.
        response = self._patch_salesperson({"city": self.city_2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["city"]["id"], self.city_2.id)
        self.salesperson.refresh_from_db()
        self.assertEqual(self.salesperson.city_id, self.city_2.id)

    def test_a_salesperson_patch_touches_only_the_fields_it_names(self):
        """tests/test_user_update.py::UserUpdateTest::test_a_salesperson_patch_touches_only_the_fields_it_names"""
        response = self._patch_salesperson(
            {"name": "Bulk Person", "email": "bulk@example.com", "city": self.city_2.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.salesperson.user.refresh_from_db()
        self.salesperson.refresh_from_db()
        self.assertEqual(self.salesperson.user.name, "Bulk Person")
        self.assertEqual(self.salesperson.user.email, "bulk@example.com")
        self.assertEqual(self.salesperson.city_id, self.city_2.id)

        self._patch_salesperson({"name": "Only Person"})
        self.salesperson.user.refresh_from_db()
        self.salesperson.refresh_from_db()
        self.assertEqual(self.salesperson.user.name, "Only Person")
        self.assertEqual(self.salesperson.user.email, "bulk@example.com")
        self.assertEqual(self.salesperson.city_id, self.city_2.id)

    def test_invalid_salesperson_payloads_are_rejected(self):
        """tests/test_user_update.py::UserUpdateTest::test_invalid_salesperson_payloads_are_rejected"""
        cases = [
            ("unknown city", {"city": 999999}),
            ("malformed phone", {"phone_number": "12345"}),
            ("phone already taken", {"phone_number": "7777777777"}),
        ]
        for label, body in cases:
            with self.subTest(case=label):
                self.assertEqual(
                    self._patch_salesperson(body).status_code, status.HTTP_400_BAD_REQUEST
                )

    def test_resending_a_salespersons_own_phone_number_is_allowed(self):
        """Same regression as for admins: an unchanged own phone must not 400.

        tests/test_user_update.py::UserUpdateTest::test_resending_a_salespersons_own_phone_number_is_allowed
        """
        response = self._patch_salesperson(
            {"phone_number": self.salesperson.user.phone_number, "name": "Same Phone Person"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.salesperson.user.refresh_from_db()
        self.assertEqual(self.salesperson.user.name, "Same Phone Person")

    def test_salesperson_payload_shape(self):
        """tests/test_user_update.py::UserUpdateTest::test_salesperson_payload_shape"""
        person = self._patch_salesperson({"name": "Payload Person"}).data
        self.assertEqual(person["role"], "salesperson")
        self.assertEqual(person["id"], self.salesperson.id)
        self.assertIn("city", person)
        for key in ("user_id", "address", "is_deleted", "deleted_by", "totp"):
            self.assertNotIn(key, person)

    # -- addressability: unknown and already-deleted rows --------------------

    def test_an_unknown_or_soft_deleted_row_is_404_for_both_verbs(self):
        """Soft-deleted rows leave the API entirely -- PATCH and DELETE both 404.

        tests/test_user_update.py::UserUpdateTest::test_an_unknown_or_soft_deleted_row_is_404_for_both_verbs
        """
        self.admin.delete(deleted_by=self.superuser)
        self.salesperson.delete(deleted_by=self.superuser)
        self.login_as(self.superuser)

        cases = [
            ("unknown admin", ADMIN_URL.format(id=999999)),
            ("deleted admin", ADMIN_URL.format(id=self.admin.id)),
            ("unknown salesperson", SALESPERSON_URL.format(id=999999)),
            ("deleted salesperson", SALESPERSON_URL.format(id=self.salesperson.id)),
        ]
        for label, url in cases:
            with self.subTest(case=label):
                self.assertEqual(
                    self.client.patch(url, {"name": "x"}, format="json").status_code,
                    status.HTTP_404_NOT_FOUND,
                )
                self.assertEqual(
                    self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND
                )

    # -- soft delete ----------------------------------------------------------

    def test_deleting_an_admin_soft_deletes_the_row(self):
        """tests/test_user_update.py::UserUpdateTest::test_deleting_an_admin_soft_deletes_the_row"""
        self.login_as(self.superuser)
        self.assertEqual(
            self.client.delete(ADMIN_URL.format(id=self.admin.id)).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_deleted)
        self.assertIsNotNone(self.admin.deleted_at)
        self.assertEqual(self.admin.deleted_by_id, self.superuser.id)

    def test_deleting_a_salesperson_soft_deletes_the_row(self):
        """Both a superuser and an app admin may do it; the deleter is recorded.

        tests/test_user_update.py::UserUpdateTest::test_deleting_a_salesperson_soft_deletes_the_row
        """
        url = SALESPERSON_URL.format(id=self.salesperson.id)
        self.login_as(self.superuser)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)

        # Same again as an app admin, on a fresh row, to pin who gets recorded.
        person = SalesPerson.objects.create(
            user=User.objects.create_user(
                phone_number="4444444444",
                name="second salesperson",
                is_verified=True,
                created_by=self.superuser,
                verified_by=self.superuser,
            ),
            city=self.city,
            created_by=self.superuser,
        )
        self.login_as(self.seed_admin)
        self.assertEqual(
            self.client.delete(SALESPERSON_URL.format(id=person.id)).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        person.refresh_from_db()
        self.assertTrue(person.is_deleted)
        self.assertIsNotNone(person.deleted_at)
        self.assertEqual(person.deleted_by_id, self.seed_admin.id)
