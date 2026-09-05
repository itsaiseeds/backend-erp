"""Client model + ClientOperations tests.

Run: bash scripts/run.sh test-unit
Node ids are given on each method docstring.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError

from aggregator.ClientOperations import (
    add_client_address,
    add_client_contact,
    add_client_transport_agency,
    create_client,
    set_or_update_primary_address,
    verify_client,
)
from aggregator.models import (
    Address,
    City,
    Client,
    Contact,
    Country,
    Pincode,
    State,
    Status,
    StatusIds,
    TransportAgency,
)
from authentication.models import Admin, SalesPerson, User
from tests.common import DMLTestCase


class ClientModelTest(DMLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.su = User.objects.get(id=1)
        cls.sp_user = User.objects.create_user(
            "9000000001", "Sales Person", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.adm_user = User.objects.create_user(
            "9000000002", "Sales Admin", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.plain_user = User.objects.create_user(
            "9000000003", "Plain User", created_by=cls.su, verified_by=cls.su, is_verified=True
        )
        cls.country = Country.objects.create(name="India", iso_code="IN", created_by=cls.su)
        cls.state = State.objects.create(name="Maharashtra", country=cls.country, created_by=cls.su)
        cls.city = City.objects.create(name="Pune", state=cls.state, created_by=cls.su)
        cls.pincode = Pincode.objects.create(code="411001", city=cls.city, created_by=cls.su)
        SalesPerson.objects.create(user=cls.sp_user, city=cls.city, created_by=cls.su)
        Admin.objects.create(user=cls.adm_user, created_by=cls.su)

    def _address(self, line="1 Main St"):
        return Address.objects.create(
            address_line_1=line,
            pincode=self.pincode,
            city=self.city,
            state=self.state,
            country=self.country,
            created_by=self.su,
        )

    def test_create_client_defaults_pending(self):
        """tests/test_client_model.py::ClientModelTest::test_create_client_defaults_pending"""
        client = create_client(
            company_name="Acme Seeds", gst_number="27AAPFU0939F1ZV", actor=self.sp_user
        )
        assert client.status.code == "VERIFICATION_PENDING"
        assert client.is_verified is False

    def test_invalid_gst_rejected(self):
        """tests/test_client_model.py::ClientModelTest::test_invalid_gst_rejected"""
        with self.assertRaises(ValidationError):
            create_client(company_name="Bad", gst_number="INVALID", actor=self.sp_user)

    def test_non_salesperson_creator_rejected(self):
        """tests/test_client_model.py::ClientModelTest::test_non_salesperson_creator_rejected"""
        with self.assertRaises(ValidationError):
            create_client(
                company_name="Bad", gst_number="27AAPFU0939F1ZW", actor=self.plain_user
            )

    def test_verify_client_by_admin(self):
        """tests/test_client_model.py::ClientModelTest::test_verify_client_by_admin"""
        client = create_client(
            company_name="Acme", gst_number="27AAPFU0939F1ZV", actor=self.sp_user
        )
        verify_client(client, self.adm_user)
        assert client.status.code == "VERIFIED"
        assert client.verified_by_id == self.adm_user.id
        assert client.verified_at is not None

    def test_verify_by_non_admin_rejected(self):
        """tests/test_client_model.py::ClientModelTest::test_verify_by_non_admin_rejected"""
        client = create_client(
            company_name="Acme", gst_number="27AAPFU0939F1ZV", actor=self.sp_user
        )
        with self.assertRaises(ValidationError):
            verify_client(client, self.plain_user)

    def test_verified_requires_verifier(self):
        """tests/test_client_model.py::ClientModelTest::test_verified_requires_verifier"""
        client = Client(
            company_name="Acme",
            gst_number="27AAPFU0939F1ZV",
            status=Status.by_id(StatusIds.VERIFIED),
            created_by=self.sp_user,
        )
        with self.assertRaises(ValidationError):
            client.full_clean()

    def test_links_resolve(self):
        """tests/test_client_model.py::ClientModelTest::test_links_resolve"""
        client = create_client(
            company_name="Acme", gst_number="27AAPFU0939F1ZV", actor=self.sp_user
        )
        add_client_address(client, self._address(), self.sp_user, label="WH", is_primary=True)
        contact = Contact.objects.create(
            name="Ravi", phone_number="9812345678", created_by=self.sp_user
        )
        add_client_contact(client, contact, self.sp_user, is_primary=True)
        agency = TransportAgency.objects.create(name="FastTrans", created_by=self.sp_user)
        add_client_transport_agency(client, agency, self.sp_user, is_primary=True)
        assert client.addresses.count() == 1
        assert client.contacts.count() == 1
        assert client.transport_agencies.count() == 1

    def test_set_or_update_primary_address_replaces(self):
        """tests/test_client_model.py::ClientModelTest::test_set_or_update_primary_address_replaces"""
        client = create_client(
            company_name="Acme", gst_number="27AAPFU0939F1ZV", actor=self.sp_user
        )
        a1 = self._address("1 Main St")
        a2 = self._address("2 Second St")
        add_client_address(client, a1, self.sp_user, is_primary=True)
        set_or_update_primary_address(client, a2, self.sp_user)
        primaries = list(
            client.client_addresses.filter(is_primary=True).values_list("address_id", flat=True)
        )
        assert primaries == [a2.id]
