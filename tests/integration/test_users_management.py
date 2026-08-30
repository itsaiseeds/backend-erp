"""Endpoint integration tests for the sales_admin admin / salesperson management.

These hit the live Django server over HTTP via the helpers in
:mod:`tests.integration.base`. ``sql/dml.sql`` seeds:

* a TOTP-enabled superuser (phone 9999999999, secret ``JBSWY3DPEHPK3PXP``),
* a TOTP-enabled application Admin (phone 7777777777, secret ``KRSXG5CTMVRXEZLU``),
* a TOTP-enabled plain user (phone 6666666666, secret ``IJQXGZJTGMFWC3LN``), and
* a minimal geography tree (country India -> state Maharashtra -> city Pune,
  id 1, pincode 411001) backing the admin ``city``/``address`` blocks.

Codes are computed with pyotp against those known secrets - there is no ORM
access in these integration tests.
"""

from __future__ import annotations

import pyotp
import pytest

from tests.integration.base import IntegrationTestCase

pytestmark = pytest.mark.integration

SUPERUSER_PHONE = "9999999999"
SUPERUSER_SECRET = "JBSWY3DPEHPK3PXP"
ADMIN_PHONE = "7777777777"
ADMIN_SECRET = "KRSXG5CTMVRXEZLU"
PLAIN_PHONE = "6666666666"
PLAIN_SECRET = "IJQXGZJTGMFWC3LN"
SEED_ADMIN_USER_ID = 3
PUNE_CITY_ID = 1
PUNE_STATE_ID = 1
PUNE_PINCODE_ID = 1
INDIA_COUNTRY_ID = 1
ADDRESS_BLOCK = {
    "line_1": "FC Road",
    "line_2": "2nd Floor, Shri Complex",
    "city": PUNE_CITY_ID,
    "state": PUNE_STATE_ID,
    "pincode": PUNE_PINCODE_ID,
    "country": INDIA_COUNTRY_ID,
}
REAL_ADDRESS = {
    "line_1": "FC Road",
    "line_2": "2nd Floor, Shri Complex",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001",
    "country": "India",
}
NA_ADDRESS = {
    "line_1": "N/A",
    "line_2": "N/A",
    "city": "N/A",
    "state": "N/A",
    "pincode": "N/A",
    "country": "N/A",
}


class UserManagementTest(IntegrationTestCase):
    """Covers the admin + salesperson create/list endpoints of the sales admin API.
    tests/integration/test_users_management.py::UserManagementTest
    """

    # -- auth helpers ---------------------------------------------------------

    def _token(self, phone: str, secret: str) -> str:
        response = self.post(
            "/api/sales_admin/auth/otp/verify",
            json={"phone_number": phone, "otp": pyotp.TOTP(secret).now()},
        )
        assert response.status_code == 200, response.text
        return response.json()["token"]

    def _auth_as(self, phone: str, secret: str) -> None:
        self.client.headers["Authorization"] = f"Token {self._token(phone, secret)}"

    def _clear_auth(self) -> None:
        self.client.headers.pop("Authorization", None)

    # -- permission gating ----------------------------------------------------

    def test_anonymous_requests_are_rejected(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_anonymous_requests_are_rejected"""
        self._clear_auth()
        for path, method in (
            ("/api/sales_admin/admins", "get"),
            ("/api/sales_admin/admins", "post"),
            ("/api/sales_admin/sales-people", "get"),
            ("/api/sales_admin/sales-people", "post"),
        ):
            response = getattr(self, method)(path, json={})
            assert response.status_code in (401, 403)

    def test_only_superuser_can_create_admin(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_only_superuser_can_create_admin"""
        payload = {
            "name": "Should Not Exist",
            "phone_number": "9000000099",
            "city": PUNE_CITY_ID,
        }
        for phone, secret in ((PLAIN_PHONE, PLAIN_SECRET), (ADMIN_PHONE, ADMIN_SECRET)):
            self._auth_as(phone, secret)
            response = self.post("/api/sales_admin/admins", json=payload)
            assert response.status_code == 403

        self._auth_as(SUPERUSER_PHONE, SUPERUSER_SECRET)
        response = self.post("/api/sales_admin/admins", json=payload)
        assert response.status_code == 201, response.text

    def test_only_admin_or_superuser_can_create_salesperson(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_only_admin_or_superuser_can_create_salesperson"""
        payload = {
            "name": "Blocked Person",
            "phone_number": "9000000088",
            "city": PUNE_CITY_ID,
        }
        self._auth_as(PLAIN_PHONE, PLAIN_SECRET)
        response = self.post("/api/sales_admin/sales-people", json=payload)
        assert response.status_code == 403

    # -- admin creation ---------------------------------------------------------

    def test_create_admin_also_creates_fallback_salesperson(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_create_admin_also_creates_fallback_salesperson"""
        self._auth_as(SUPERUSER_PHONE, SUPERUSER_SECRET)
        response = self.post(
            "/api/sales_admin/admins",
            json={
                "name": "Vikram Kumar",
                "email": "vikram@example.com",
                "phone_number": "9000000001",
                "can_update_stock_count": True,
                "city": PUNE_CITY_ID,
                "address": ADDRESS_BLOCK,
            },
        )
        assert response.status_code == 201, response.text
        admin = response.json()

        assert admin["name"] == "Vikram Kumar"
        assert admin["email"] == "vikram@example.com"
        assert admin["phone_number"] == "9000000001"
        assert admin["role"] == "admin"
        assert admin["is_deleted"] is False
        assert admin["deleted_by"] is None
        assert admin["can_update_stock_count"] is True
        assert admin["is_salesperson"] is True
        assert admin["city"]["id"] == PUNE_CITY_ID
        assert admin["address"] == REAL_ADDRESS

        users = self.get("/api/sales_admin/sales-people").json()
        fallback = next(
            item for item in users if item["user_id"] == admin["user_id"]
        )
        assert fallback["role"] == "salesperson"
        assert fallback["city"]["id"] == PUNE_CITY_ID
        assert "address" not in fallback

    def test_create_admin_duplicate_phone_rejected(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_create_admin_duplicate_phone_rejected"""
        self._auth_as(SUPERUSER_PHONE, SUPERUSER_SECRET)
        payload = {
            "name": "Duplicate",
            "phone_number": "9000000002",
            "city": PUNE_CITY_ID,
        }
        first = self.post("/api/sales_admin/admins", json=payload)
        assert first.status_code == 201, first.text
        second = self.post("/api/sales_admin/admins", json=payload)
        assert second.status_code == 400

    def test_create_admin_invalid_payload_rejected(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_create_admin_invalid_payload_rejected"""
        self._auth_as(SUPERUSER_PHONE, SUPERUSER_SECRET)
        cases = [
            {"name": "No Phone", "city": PUNE_CITY_ID},
            {"name": "Bad Phone", "phone_number": "12345", "city": PUNE_CITY_ID},
            {"name": "No City", "phone_number": "9000000003"},
        ]
        for payload in cases:
            response = self.post("/api/sales_admin/admins", json=payload)
            assert response.status_code == 400, payload

    def test_create_admin_invalid_address_rejected(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_create_admin_invalid_address_rejected"""
        self._auth_as(SUPERUSER_PHONE, SUPERUSER_SECRET)
        cases = [
            {"address": {}},
            {"address": {"line_1": "Only a line"}},
            {"address": {"line_1": "Line", "city": PUNE_CITY_ID, "state": 99}},
        ]
        for address in cases:
            response = self.post(
                "/api/sales_admin/admins",
                json={
                    "name": "Bad Address",
                    "phone_number": "9000000004",
                    "city": PUNE_CITY_ID,
                    "address": address,
                },
            )
            assert response.status_code == 400, address

    def test_list_admins_skips_soft_deleted(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_list_admins_skips_soft_deleted"""
        self._auth_as(SUPERUSER_PHONE, SUPERUSER_SECRET)
        created = self.post(
            "/api/sales_admin/admins",
            json={
                "name": "Vikram Kumar",
                "phone_number": "9000000050",
                "city": PUNE_CITY_ID,
            },
        )
        assert created.status_code == 201, created.text

        response = self.get("/api/sales_admin/admins")
        assert response.status_code == 200
        admins = response.json()
        assert isinstance(admins, list)
        assert any(item["name"] == "Vikram Kumar" for item in admins)
        seed_admin = next(item for item in admins if item["user_id"] == SEED_ADMIN_USER_ID)
        assert seed_admin["role"] == "admin"
        assert seed_admin["is_salesperson"] is False
        assert seed_admin["city"]["name"] == "N/A"
        assert seed_admin["address"] == NA_ADDRESS
        assert all(item["role"] == "admin" for item in admins)

    # -- salesperson creation ---------------------------------------------------

    def test_create_salesperson_by_admin(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_create_salesperson_by_admin"""
        self._auth_as(ADMIN_PHONE, ADMIN_SECRET)
        response = self.post(
            "/api/sales_admin/sales-people",
            json={
                "name": "Ramesh Patil",
                "phone_number": "9000000011",
                "city": PUNE_CITY_ID,
                "address": ADDRESS_BLOCK,
            },
        )
        assert response.status_code == 201, response.text
        person = response.json()
        assert person["name"] == "Ramesh Patil"
        assert person["email"] is None
        assert person["phone_number"] == "9000000011"
        assert person["role"] == "salesperson"
        assert person["is_deleted"] is False
        assert person["city"]["id"] == PUNE_CITY_ID
        assert "address" not in person

    def test_create_salesperson_by_superuser(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_create_salesperson_by_superuser"""
        self._auth_as(SUPERUSER_PHONE, SUPERUSER_SECRET)
        response = self.post(
            "/api/sales_admin/sales-people",
            json={
                "name": "Super Hire",
                "phone_number": "9000000012",
                "city": PUNE_CITY_ID,
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["role"] == "salesperson"

    def test_list_sales_people(self):
        """tests/integration/test_users_management.py::UserManagementTest::test_list_sales_people"""
        self._auth_as(ADMIN_PHONE, ADMIN_SECRET)
        created = self.post(
            "/api/sales_admin/sales-people",
            json={
                "name": "Ramesh Patil",
                "phone_number": "9000000051",
                "city": PUNE_CITY_ID,
            },
        )
        assert created.status_code == 201, created.text

        response = self.get("/api/sales_admin/sales-people")
        assert response.status_code == 200
        people = response.json()
        assert isinstance(people, list)
        assert any(item["name"] == "Ramesh Patil" for item in people)
        assert all(item["role"] == "salesperson" for item in people)
        assert all("city" in item for item in people)
