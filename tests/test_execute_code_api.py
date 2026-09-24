"""``POST /api/execute-code/`` and its ``/execute-code/`` UI page.

Who may call it (the ``execute_python_code`` permission, whatever the role) is
proven once in ``tests/test_view_contracts.py``.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import status

from aggregator.models import Party
from authentication.models import Admin
from tests.common import WebApiTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"
EXECUTE_URL = "/api/execute-code/"
PAGE_URL = "/execute-code/"


class ExecuteCodeApiTest(WebApiTestCase):
    """tests/test_execute_code_api.py::ExecuteCodeApiTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.runner = User.objects.create_user(
            phone_number="9000000901",
            name="Code Runner",
            is_verified=True,
            created_by=superuser,
            verified_by=superuser,
        )
        Admin.objects.create(user=cls.runner, created_by=superuser)
        cls.runner.user_permissions.add(Permission.objects.get(codename="execute_python_code"))

    def setUp(self):
        super().setUp()
        self.login_as(self.runner)

    def _run(self, code):
        resp = self.client.post(EXECUTE_URL, {"code": code}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        return resp.data

    def test_stdout_and_result_are_returned_with_models_in_scope(self):
        """tests/test_execute_code_api.py::ExecuteCodeApiTest::test_stdout_and_result_are_returned_with_models_in_scope"""
        data = self._run(f"print('hello')\nresult = User.objects.filter(id={self.runner.id}).count()")

        self.assertTrue(data["success"])
        self.assertEqual(data["stdout"], "hello\n")
        self.assertEqual(data["result"], "1")
        self.assertIsNone(data["error"])

    def test_model_enums_are_in_scope(self):
        """tests/test_execute_code_api.py::ExecuteCodeApiTest::test_model_enums_are_in_scope"""
        data = self._run(
            "result = (StatusIds.CONFIRMED.value, StageIds.BREEDER.name, "
            "InwardRawMaterialStatus.IN_USE.value)"
        )

        self.assertTrue(data["success"], data["error"])
        self.assertEqual(data["result"], "(3, 'BREEDER', 'in_use')")

    def test_a_successful_write_is_committed(self):
        """tests/test_execute_code_api.py::ExecuteCodeApiTest::test_a_successful_write_is_committed"""
        code = (
            "Party.objects.create(name='Script Party', city_id=1, "
            f"created_by=User.objects.get(id={self.runner.id}))"
        )
        data = self._run(code)

        self.assertTrue(data["success"], data["error"])
        self.assertTrue(Party.objects.filter(name="Script Party").exists())

    def test_a_raised_exception_rolls_back_and_returns_the_traceback(self):
        """tests/test_execute_code_api.py::ExecuteCodeApiTest::test_a_raised_exception_rolls_back_and_returns_the_traceback"""
        code = (
            "Party.objects.create(name='Doomed Party', city_id=1, "
            f"created_by=User.objects.get(id={self.runner.id}))\n"
            "print('before')\n"
            "raise ValueError('boom')"
        )
        data = self._run(code)

        self.assertFalse(data["success"])
        self.assertIn("ValueError: boom", data["error"])
        self.assertEqual(data["stdout"], "before\n")
        self.assertIsNone(data["result"])
        self.assertFalse(Party.objects.filter(name="Doomed Party").exists())

    def test_blank_code_is_refused(self):
        """tests/test_execute_code_api.py::ExecuteCodeApiTest::test_blank_code_is_refused"""
        resp = self.client.post(EXECUTE_URL, {"code": ""}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_ui_page_is_served_only_to_permission_holders(self):
        """Logged out -> sent to the sales-admin login; no permission -> 403.

        tests/test_execute_code_api.py::ExecuteCodeApiTest::test_the_ui_page_is_served_only_to_permission_holders
        """
        page = self.client.get(PAGE_URL)
        self.assertEqual(page.status_code, status.HTTP_200_OK)
        self.assertContains(page, "<button id=\"run\"")
        self.assertIn("csrftoken", page.cookies)
        # The autocomplete catalogue mirrors the execution scope.
        catalogue = page.context["catalogue"]
        self.assertIn("status", catalogue["models"]["Order"]["fields"])
        self.assertIn("objects", catalogue["models"]["Order"]["managers"])
        self.assertIn("CONFIRMED", catalogue["enums"]["StatusIds"])

        self.clear_auth()
        self.assertRedirects(
            self.client.get(PAGE_URL), "/sales-admin/", fetch_redirect_response=False
        )

        outsider = User.objects.create_user(
            phone_number="9000000902",
            name="No Permission",
            is_verified=True,
            created_by=self.runner,
            verified_by=self.runner,
        )
        self.login_as(outsider)
        self.assertEqual(self.client.get(PAGE_URL).status_code, status.HTTP_403_FORBIDDEN)
