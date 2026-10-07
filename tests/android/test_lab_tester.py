"""ORM-backed tests for the lab-tester role: Android lab endpoints, the godown and
admin restrictions around the lot lifecycle, and the admin lab views.

The verdict rules themselves (Pass -> In Use, Fail -> Rejected, the packed-stock
guard, computed figures) are proven in ``tests/test_lab_testing_operations.py``;
here we show the endpoints reach them and who may call what. The stock ledger
guard (``DMLTestCase``) runs after every test.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from aggregator import InventoryOperations
from aggregator.InwardOperations import today
from aggregator.models import InwardRawMaterial, LabTesting, Party, Product, ProductPackaging
from authentication.models import Admin, GodownManager, LabTester, SalesPerson, User
from tests.android.common import AndroidApiTestCase

BASE = "/android/api/v1/"
WEB = "/api/sales-admin/"
LOGIN_URL = BASE + "auth/login"
REAUTH_URL = BASE + "auth/reauthenticate"
PENDING_URL = BASE + "lab/pending-lots"
TESTS_URL = BASE + "lab/lab-testings"
GODOWN_LOTS_URL = BASE + "godown/inward-raw-materials"
TOTP_SECRET = "KRSXG5DSNFXGOIDB"


def _test_url(public_id: str) -> str:
    return BASE + f"lab/lab-testing/{public_id}"


class LabTesterApiTest(AndroidApiTestCase):
    """tests/android/test_lab_tester.py::LabTesterApiTest"""

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

        cls.tester = make_user(
            "7200000001", "lab tester", totp_secret=TOTP_SECRET, totp_enabled=True
        )
        LabTester.objects.create(user=cls.tester, created_by=cls.superuser)
        cls.godown = make_user("7200000002", "godown manager")
        GodownManager.objects.create(user=cls.godown, created_by=cls.superuser)
        cls.sales = make_user("7200000003", "sales person")
        SalesPerson.objects.create(user=cls.sales, city_id=1, created_by=cls.superuser)
        cls.admin = make_user("7200000004", "admin")
        Admin.objects.create(user=cls.admin, can_update_stock_count=True, created_by=cls.superuser)

        cls.product = Product.objects.get(name="SAI-33")
        cls.party = Party.objects.create(name="Lab API Party", city_id=1, created_by=cls.superuser)

    # -- clients & helpers ----------------------------------------------------------

    @staticmethod
    def _android(user: User) -> APIClient:
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    @staticmethod
    def _web(user: User) -> APIClient:
        client = APIClient()
        client.force_login(user)
        return client

    def setUp(self):
        super().setUp()
        self.as_tester = self._android(self.tester)
        self.as_godown = self._android(self.godown)
        self.as_sales = self._android(self.sales)
        self.as_admin = self._web(self.admin)

    def _book(self, quantity_kg="100", lot_no="SUP-1") -> str:
        """Book a lot the way a godown manager does; returns its public id."""
        response = self.as_godown.post(
            GODOWN_LOTS_URL,
            {
                "product": self.product.public_id,
                "party": self.party.id,
                "lot_no": lot_no,
                "quantity_kg": quantity_kg,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.data["public_id"]

    def _body(self, lot: str, **overrides) -> dict:
        return {
            "inward_raw_material": lot,
            "number_of_plants": 200,
            "female_count": 3,
            "ot_count": 1,
            "result": "Pass",
            "comment": "healthy stand",
            **overrides,
        }

    def _submit(self, lot: str, **overrides):
        return self.as_tester.post(TESTS_URL, self._body(lot, **overrides), format="json")

    def _lot(self, lot: str) -> dict:
        """The lot as the admin list shows it."""
        response = self.as_admin.get(WEB + "inward-raw-materials", {"public_id": lot})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["total_count"], 1)
        return response.data["results"][0]

    def _pack_a_bag(self) -> None:
        packaging = ProductPackaging.objects.create(
            product=self.product,
            packet_weight=Decimal("2.500"),
            packets=4,
            selling_price=Decimal("1000.00"),
            created_by=self.superuser,
        )
        InventoryOperations.record_stock_count(
            product_packaging=packaging, bags=1, actor=self.superuser
        )

    # -- login ---------------------------------------------------------------------

    def test_a_lab_tester_logs_in_and_reauthenticates_with_their_role(self):
        """Lab testers sign in with TOTP like the other Android roles.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_a_lab_tester_logs_in_and_reauthenticates_with_their_role
        """
        login = self.client.post(
            LOGIN_URL,
            {"phone_number": self.tester.phone_number, "otp": self.tester.totp.now()},
            format="json",
        )

        self.assertEqual(login.status_code, 200, login.content)
        user = login.data["user"]
        self.assertEqual(user["role"], "lab_tester")
        self.assertEqual(
            (user["is_sales_person"], user["is_godown_manager"], user["is_lab_tester"]),
            (False, False, True),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
        reauth = self.client.get(REAUTH_URL)
        self.assertEqual(reauth.status_code, 200, reauth.content)
        self.assertTrue(reauth.data["user"]["is_lab_tester"])

    # -- the queue --------------------------------------------------------------------

    def test_pending_lots_is_the_lab_testing_queue_oldest_first(self):
        """Only lots still in Lab Testing, oldest first; a decided lot leaves the queue.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_pending_lots_is_the_lab_testing_queue_oldest_first
        """
        first = self._book(lot_no="SUP-A")
        second = self._book(lot_no="SUP-B")
        decided = self._book(lot_no="SUP-C")
        self.assertEqual(self._submit(decided).status_code, 201)

        response = self.as_tester.get(PENDING_URL)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual([row["public_id"] for row in response.data["results"]], [first, second])
        for row in response.data["results"]:
            self.assertEqual(row["status"], "Lab Testing")
            self.assertIsNone(row["lab_testing"])

    # -- submitting a test ------------------------------------------------------------------

    def test_pass_submits_the_test_and_makes_the_lot_in_use(self):
        """201 with the computed figures; the lot is In Use from today and links its test.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_pass_submits_the_test_and_makes_the_lot_in_use
        """
        lot = self._book()

        response = self._submit(lot, result="Pass")

        self.assertEqual(response.status_code, 201, response.content)
        data = response.data
        self.assertTrue(data["public_id"].startswith("LT-"))
        self.assertEqual(data["result"], "Pass")
        self.assertEqual(data["genetical_impurity"], "2.00")
        self.assertEqual(data["grow_out_test"], "98.00")
        self.assertEqual(data["number_of_plants"], 200)
        self.assertEqual(data["comment"], "healthy stand")
        self.assertEqual(data["tested_by"], {"id": self.tester.id, "name": "lab tester"})
        self.assertEqual(data["inward_raw_material"]["public_id"], lot)
        self.assertEqual(data["inward_raw_material"]["status"], "In Use")

        row = self._lot(lot)
        self.assertEqual(row["status"], "In Use")
        self.assertEqual(row["effective_date"], today().isoformat())
        self.assertEqual(
            row["lab_testing"],
            {"public_id": data["public_id"], "result": "Pass", "grow_out_test": "98.00"},
        )

    def test_fail_submits_the_test_and_rejects_the_lot(self):
        """tests/android/test_lab_tester.py::LabTesterApiTest::test_fail_submits_the_test_and_rejects_the_lot"""
        lot = self._book()

        response = self._submit(lot, result="Fail")

        self.assertEqual(response.status_code, 201, response.content)
        row = self._lot(lot)
        self.assertEqual(row["status"], "Rejected")
        self.assertEqual(row["effective_date"], today().isoformat())

    def test_invalid_submissions_are_a_400_and_leave_the_lot_untouched(self):
        """Negative-making or malformed input never reaches the lot.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_invalid_submissions_are_a_400_and_leave_the_lot_untouched
        """
        lot = self._book()
        cases = {
            "more female + OT than plants": {"female_count": 150, "ot_count": 60},
            "zero plants": {"number_of_plants": 0},
            "negative female count": {"female_count": -1},
            "negative OT": {"ot_count": -1},
            "unknown result": {"result": "Maybe"},
            "no result": {"result": None},
            "unknown lot": {"inward_raw_material": "IR-DOESNOTEXIST"},
        }
        for label, overrides in cases.items():
            with self.subTest(label):
                response = self._submit(lot, **overrides)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn("detail", response.data)

        missing = self.as_tester.post(TESTS_URL, {"inward_raw_material": lot}, format="json")
        self.assertEqual(missing.status_code, 400)
        self.assertFalse(LabTesting.objects.exists())
        self.assertEqual(self._lot(lot)["status"], "Lab Testing")

    def test_a_lot_already_decided_cannot_be_submitted_again(self):
        """A second submit on an In Use lot is refused; editing is the way to change it.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_a_lot_already_decided_cannot_be_submitted_again
        """
        lot = self._book()
        self.assertEqual(self._submit(lot).status_code, 201)

        response = self._submit(lot, result="Fail")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Only a lot in Lab Testing", response.data["detail"])
        self.assertEqual(LabTesting.objects.count(), 1)

    # -- reading and editing one test ------------------------------------------------------------

    def test_one_test_can_be_read_in_detail_by_the_tester_and_the_admin(self):
        """Both clients get the full record; an unknown id is a 404.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_one_test_can_be_read_in_detail_by_the_tester_and_the_admin
        """
        lot = self._book()
        test_id = self._submit(lot).data["public_id"]

        android = self.as_tester.get(_test_url(test_id))
        web = self.as_admin.get(WEB + f"lab-testing/{test_id}")

        self.assertEqual(android.status_code, 200, android.content)
        self.assertEqual(web.status_code, 200, web.content)
        self.assertEqual(android.data, web.data)
        self.assertEqual(android.data["grow_out_test"], "98.00")
        self.assertEqual(android.data["inward_raw_material"]["public_id"], lot)
        self.assertEqual(self.as_tester.get(_test_url("LT-DOESNOTEXIST")).status_code, 404)
        self.assertEqual(self.as_admin.get(WEB + "lab-testing/LT-DOESNOTEXIST").status_code, 404)

    def test_the_inputs_of_a_test_can_be_corrected_without_moving_the_lot(self):
        """PATCH of the counts recomputes the figures; the verdict and the lot stay.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_the_inputs_of_a_test_can_be_corrected_without_moving_the_lot
        """
        lot = self._book()
        test_id = self._submit(lot).data["public_id"]

        response = self.as_tester.patch(
            _test_url(test_id),
            {"female_count": 9, "ot_count": 1, "comment": "recounted"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["genetical_impurity"], "5.00")
        self.assertEqual(response.data["grow_out_test"], "95.00")
        self.assertEqual(response.data["comment"], "recounted")
        self.assertEqual(response.data["result"], "Pass")
        self.assertEqual(self._lot(lot)["status"], "In Use")

    def test_a_patch_that_makes_the_counts_impossible_is_a_400(self):
        """Partial edits are checked against the stored counts too.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_a_patch_that_makes_the_counts_impossible_is_a_400
        """
        lot = self._book()
        test_id = self._submit(lot, number_of_plants=10, female_count=1, ot_count=1).data[
            "public_id"
        ]

        response = self.as_tester.patch(_test_url(test_id), {"female_count": 10}, format="json")

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(self.as_tester.get(_test_url(test_id)).data["female_count"], 1)

    def test_pass_to_fail_is_refused_while_bags_are_packed_from_the_lot(self):
        """Failing the lot would pull packed kilograms out of the pool: 400, nothing moves.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_pass_to_fail_is_refused_while_bags_are_packed_from_the_lot
        """
        lot = self._book("100")
        test_id = self._submit(lot).data["public_id"]
        self._pack_a_bag()

        refused = self.as_tester.patch(_test_url(test_id), {"result": "Fail"}, format="json")

        self.assertEqual(refused.status_code, 400, refused.content)
        self.assertIn("already packed", refused.data["detail"])
        self.assertEqual(self._lot(lot)["status"], "In Use")
        self.assertEqual(self.as_tester.get(_test_url(test_id)).data["result"], "Pass")

    def test_pass_to_fail_is_allowed_when_nothing_is_packed_from_the_lot(self):
        """tests/android/test_lab_tester.py::LabTesterApiTest::test_pass_to_fail_is_allowed_when_nothing_is_packed_from_the_lot"""
        lot = self._book("100")
        test_id = self._submit(lot).data["public_id"]

        response = self.as_tester.patch(_test_url(test_id), {"result": "Fail"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["result"], "Fail")
        row = self._lot(lot)
        self.assertEqual(row["status"], "Rejected")
        self.assertEqual(row["effective_date"], today().isoformat())

    def test_fail_to_pass_is_always_allowed(self):
        """tests/android/test_lab_tester.py::LabTesterApiTest::test_fail_to_pass_is_always_allowed"""
        lot = self._book()
        test_id = self._submit(lot, result="Fail").data["public_id"]

        response = self.as_tester.patch(_test_url(test_id), {"result": "Pass"}, format="json")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["result"], "Pass")
        row = self._lot(lot)
        self.assertEqual(row["status"], "In Use")
        self.assertEqual(row["effective_date"], today().isoformat())

    # -- who may call what ------------------------------------------------------------------------

    def test_only_a_lab_tester_may_use_the_lab_endpoints(self):
        """Other Android roles get 403 and an anonymous caller 401, on every lab route.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_only_a_lab_tester_may_use_the_lab_endpoints
        """
        lot = self._book()
        test_id = self._submit(lot).data["public_id"]
        routes = [
            ("get", PENDING_URL),
            ("get", TESTS_URL),
            ("post", TESTS_URL),
            ("get", _test_url(test_id)),
            ("patch", _test_url(test_id)),
        ]
        for who, client in (("godown manager", self.as_godown), ("sales person", self.as_sales)):
            for method, url in routes:
                with self.subTest(who=who, method=method, url=url):
                    response = getattr(client, method)(url, {}, format="json")
                    self.assertEqual(response.status_code, 403, response.content)
        for method, url in routes:
            with self.subTest(who="anonymous", method=method, url=url):
                response = getattr(APIClient(), method)(url, {}, format="json")
                self.assertEqual(response.status_code, 401)

    def test_a_lab_tester_cannot_use_the_godown_endpoints(self):
        """tests/android/test_lab_tester.py::LabTesterApiTest::test_a_lab_tester_cannot_use_the_godown_endpoints"""
        lot = self._book()

        self.assertEqual(self.as_tester.get(GODOWN_LOTS_URL).status_code, 403)
        self.assertEqual(
            self.as_tester.patch(BASE + f"godown/inward-raw-material/{lot}", {}).status_code, 403
        )
        self.assertEqual(
            self.as_tester.delete(BASE + f"godown/inward-raw-material/{lot}").status_code, 403
        )

    def test_a_lab_tester_can_register_a_device_and_read_notifications(self):
        """Push and the inbox are open to every Android role.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_a_lab_tester_can_register_a_device_and_read_notifications
        """
        register = self.as_tester.post(
            BASE + "devices/register", {"fcm_token": "tester-token"}, format="json"
        )
        inbox = self.as_tester.get(BASE + "notifications")

        self.assertEqual(register.status_code, 204, register.content)
        self.assertEqual(inbox.status_code, 200, inbox.content)

    def test_a_removed_lab_tester_is_logged_out_everywhere(self):
        """Soft-deleting the profile revokes the token and the role.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_a_removed_lab_tester_is_logged_out_everywhere
        """
        self.assertEqual(self.as_tester.get(PENDING_URL).status_code, 200)

        self.tester.lab_tester_profile.mark_deleted(self.superuser)

        self.assertEqual(self.as_tester.get(PENDING_URL).status_code, 401)
        login = self.client.post(
            LOGIN_URL,
            {"phone_number": self.tester.phone_number, "otp": self.tester.totp.now()},
            format="json",
        )
        self.assertEqual(login.status_code, 400)

    # -- godown: no lifecycle ---------------------------------------------------------------------

    def test_a_godown_manager_can_no_longer_change_a_lots_status_or_sampling_date(self):
        """PATCH with either field is a 400; an empty PATCH returns the lot unchanged.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_a_godown_manager_can_no_longer_change_a_lots_status_or_sampling_date
        """
        lot = self._book()
        url = BASE + f"godown/inward-raw-material/{lot}"

        for body in (
            {"status": "In Use"},
            {"status": "Rejected"},
            {"lab_sampling_date": today().isoformat()},
        ):
            with self.subTest(body=body):
                response = self.as_godown.patch(url, body, format="json")
                self.assertEqual(response.status_code, 400, response.content)

        unchanged = self.as_godown.patch(url, {}, format="json")
        self.assertEqual(unchanged.status_code, 200, unchanged.content)
        self.assertEqual(unchanged.data["status"], "Lab Testing")
        self.assertEqual(self._lot(lot)["status"], "Lab Testing")

    def test_a_godown_manager_can_still_book_and_delete_a_lot(self):
        """Booking and correcting a mistyped lot remain the godown manager's job.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_a_godown_manager_can_still_book_and_delete_a_lot
        """
        lot = self._book()

        deleted = self.as_godown.delete(BASE + f"godown/inward-raw-material/{lot}")

        self.assertEqual(deleted.status_code, 204, deleted.content)
        self.assertFalse(InwardRawMaterial.objects.filter(public_id=lot).exists())

    # -- admin: revert only ------------------------------------------------------------------------

    def test_an_admin_can_no_longer_move_a_lot_out_of_lab_testing(self):
        """The forward flips are the lab tester's alone: both are a 400 with the reason.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_an_admin_can_no_longer_move_a_lot_out_of_lab_testing
        """
        lot = self._book()
        url = WEB + f"inward-raw-material/{lot}"

        for target in ("In Use", "Rejected"):
            with self.subTest(target=target):
                response = self.as_admin.patch(url, {"status": target}, format="json")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn("Only a lab tester", response.data["detail"])
        self.assertEqual(self._lot(lot)["status"], "Lab Testing")

    def test_an_admin_can_send_a_decided_lot_back_and_it_is_retested_on_the_same_record(self):
        """In Use / Rejected -> Lab Testing empties the result; the re-test reuses the LT row.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_an_admin_can_send_a_decided_lot_back_and_it_is_retested_on_the_same_record
        """
        lot = self._book()
        test_id = self._submit(lot, result="Pass").data["public_id"]

        revert = self.as_admin.patch(
            WEB + f"inward-raw-material/{lot}", {"status": "Lab Testing"}, format="json"
        )

        self.assertEqual(revert.status_code, 200, revert.content)
        self.assertEqual(revert.data["status"], "Lab Testing")
        self.assertIsNone(revert.data["effective_date"])
        self.assertEqual(
            revert.data["lab_testing"],
            {"public_id": test_id, "result": None, "grow_out_test": "98.00"},
        )
        queue = self.as_tester.get(PENDING_URL)
        self.assertEqual([row["public_id"] for row in queue.data["results"]], [lot])
        self.assertEqual(queue.data["results"][0]["lab_testing"]["public_id"], test_id)

        retest = self._submit(lot, result="Fail", number_of_plants=100, female_count=0, ot_count=0)

        self.assertEqual(retest.status_code, 201, retest.content)
        self.assertEqual(retest.data["public_id"], test_id)
        self.assertEqual(LabTesting.objects.count(), 1)
        self.assertEqual(self._lot(lot)["status"], "Rejected")

    def test_reverting_an_in_use_lot_whose_kilograms_are_packed_is_still_refused(self):
        """The existing packed-stock guard on a revert is untouched.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_reverting_an_in_use_lot_whose_kilograms_are_packed_is_still_refused
        """
        lot = self._book("100")
        self._submit(lot)
        self._pack_a_bag()

        response = self.as_admin.patch(
            WEB + f"inward-raw-material/{lot}", {"status": "Lab Testing"}, format="json"
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("already packed", response.data["detail"])
        self.assertEqual(self._lot(lot)["status"], "In Use")

    # -- admin: lab views ----------------------------------------------------------------------------

    def test_the_admin_lists_lab_tests_and_filters_by_result(self):
        """tests/android/test_lab_tester.py::LabTesterApiTest::test_the_admin_lists_lab_tests_and_filters_by_result"""
        passed = self._submit(self._book(lot_no="SUP-P"), result="Pass").data["public_id"]
        failed = self._submit(self._book(lot_no="SUP-F"), result="Fail").data["public_id"]

        everything = self.as_admin.get(WEB + "lab-testings")
        only_failed = self.as_admin.get(WEB + "lab-testings", {"result": "Fail"})
        tester_view = self.as_tester.get(TESTS_URL, {"result": "Pass"})

        self.assertEqual(everything.status_code, 200, everything.content)
        self.assertEqual({r["public_id"] for r in everything.data["results"]}, {passed, failed})
        self.assertEqual([r["public_id"] for r in only_failed.data["results"]], [failed])
        self.assertEqual([r["public_id"] for r in tester_view.data["results"]], [passed])
        self.assertIn("available_filters", everything.data)

    def test_only_an_admin_may_use_the_admin_lab_views(self):
        """A sales person's session is refused, as is an anonymous caller.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_only_an_admin_may_use_the_admin_lab_views
        """
        test_id = self._submit(self._book()).data["public_id"]
        urls = [WEB + "lab-testings", WEB + f"lab-testing/{test_id}", WEB + "lab-testers"]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self._web(self.sales).get(url).status_code, 403)
                self.assertEqual(APIClient().get(url).status_code, 401)

    # -- admin: managing lab testers ------------------------------------------------------------------

    def test_an_admin_hires_lists_edits_and_removes_a_lab_tester(self):
        """The same lifecycle as a godown manager: create (with QR), list, patch, delete.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_an_admin_hires_lists_edits_and_removes_a_lab_tester
        """
        created = self.as_admin.post(
            WEB + "lab-testers",
            {"name": "New Tester", "phone_number": "7200000099", "email": "new@example.com"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.data["role"], "lab_tester")
        self.assertIn("provisioning_uri", created.data["totp"])
        tester_id = created.data["id"]
        user = User.objects.get(phone_number="7200000099")
        self.assertTrue(user.is_lab_tester)
        self.assertTrue(user.is_verified)

        listing = self.as_admin.get(WEB + "lab-testers")
        self.assertIn(tester_id, [row["id"] for row in listing.data])

        patched = self.as_admin.patch(
            WEB + f"lab-testers/{tester_id}", {"name": "Renamed"}, format="json"
        )
        self.assertEqual(patched.status_code, 200, patched.content)
        self.assertEqual(patched.data["name"], "Renamed")

        rotated = self.as_admin.post(WEB + f"lab-testers/{tester_id}/rotate-qr")
        self.assertEqual(rotated.status_code, 200, rotated.content)
        self.assertIn("provisioning_uri", rotated.data["totp"])

        deleted = self.as_admin.delete(WEB + f"lab-testers/{tester_id}")
        self.assertEqual(deleted.status_code, 204, deleted.content)
        self.assertFalse(User.objects.get(pk=user.pk).is_lab_tester)
        remaining = self.as_admin.get(WEB + "lab-testers")
        self.assertNotIn(tester_id, [row["id"] for row in remaining.data])

    def test_a_lab_tester_needs_a_unique_phone_number_and_an_admin_to_create_one(self):
        """tests/android/test_lab_tester.py::LabTesterApiTest::test_a_lab_tester_needs_a_unique_phone_number_and_an_admin_to_create_one"""
        duplicate = self.as_admin.post(
            WEB + "lab-testers",
            {"name": "Dup", "phone_number": self.tester.phone_number},
            format="json",
        )
        by_sales = self._web(self.sales).post(
            WEB + "lab-testers", {"name": "X", "phone_number": "7200000098"}, format="json"
        )

        self.assertEqual(duplicate.status_code, 400, duplicate.content)
        self.assertEqual(by_sales.status_code, 403)

    def test_the_web_login_reports_whether_the_caller_may_create_lab_testers(self):
        """can_create_lab_tester rides along with the other capability flags.

        tests/android/test_lab_tester.py::LabTesterApiTest::test_the_web_login_reports_whether_the_caller_may_create_lab_testers
        """
        admin = self.as_admin.get("/api/utilities/reauthenticate")
        sales = self._web(self.sales).get("/api/utilities/reauthenticate")

        self.assertEqual(admin.status_code, 200, admin.content)
        self.assertEqual(sales.status_code, 200, sales.content)
        self.assertTrue(admin.data["can_create_lab_tester"])
        self.assertFalse(sales.data["can_create_lab_tester"])
