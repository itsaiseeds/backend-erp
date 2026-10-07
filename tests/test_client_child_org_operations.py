"""Get-or-create rules for client child orgs ("booked for").

``ClientChildOrgOperations.resolve_child_org`` is exercised directly; the
endpoints that call it are covered in the order API tests.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from aggregator.ClientChildOrgOperations import (
    child_org_payload,
    child_org_summary_payload,
    client_child_orgs,
    resolve_child_org,
)
from aggregator.ClientOperations import create_client_with_details
from aggregator.models import (
    Address,
    City,
    ClientChildOrg,
    Country,
    Pincode,
    State,
)
from authentication.models import SalesPerson
from tests.common import DMLTestCase

User = get_user_model()

SUPERUSER_PHONE = "9999999999"


class ResolveChildOrgTest(DMLTestCase):
    """tests/test_client_child_org_operations.py::ResolveChildOrgTest"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superuser = User.objects.get(phone_number=SUPERUSER_PHONE)
        cls.country = Country.objects.get(name="India")
        cls.state = State.objects.get(name="Gujarat", country=cls.country)
        cls.city = City.objects.get(name="Surat", state=cls.state)
        cls.other_city = City.objects.get(name="Ahmedabad", state=cls.state)
        cls.sales_person = User.objects.create_user(
            phone_number="9000000801",
            name="Sales One",
            is_verified=True,
            created_by=cls.superuser,
            verified_by=cls.superuser,
        )
        SalesPerson.objects.create(
            user=cls.sales_person, city=cls.city, created_by=cls.superuser
        )
        cls.acme = cls._client("Acme Seeds", "27AAPFU0939F1ZV")
        cls.rival = cls._client("Rival Seeds", "27AAPFU0939F1ZB")

    @classmethod
    def _client(cls, company_name, gst):
        return create_client_with_details(
            company_name=company_name,
            company_phone="9876543210",
            gst_number=gst,
            addresses=[
                {
                    "line_1": "1 Ring Road",
                    "line_2": "",
                    "pincode": "395007",
                    "city": cls.city,
                    "state": cls.state,
                    "country": cls.country,
                    "label": "Warehouse",
                    "is_primary": True,
                }
            ],
            contacts=[{"name": "Ramesh", "phone_number": "9876500001"}],
            transport_agencies=[{"name": f"{company_name} Transport"}],
            actor=cls.sales_person,
        )

    def _address(self, **overrides):
        data = {
            "line_1": "9 Mill Road",
            "line_2": "",
            "pincode": "394185",
            "city": self.city,
            "state": self.state,
            "country": self.country,
        }
        data.update(overrides)
        return data

    def _new(self, **overrides):
        data = {
            "party_name": "Shree Krishna Traders",
            "village_name": "Kamrej",
            "address": self._address(),
        }
        data.update(overrides)
        return data

    def _resolve(self, data, client=None):
        return resolve_child_org(client or self.acme, data, self.sales_person)

    def _refused(self, data, fragment, client=None):
        with self.assertRaises(ValidationError) as caught:
            self._resolve(data, client)
        self.assertIn(fragment, " ".join(caught.exception.messages))

    # -- create ---------------------------------------------------------------

    def test_a_new_pair_creates_the_child_and_its_address(self):
        addresses = Address.objects.count()
        child = self._resolve(
            self._new(transport_name=" Patel Roadways ", contact_number="9876543210")
        )
        self.assertEqual(ClientChildOrg.objects.count(), 1)
        self.assertEqual(Address.objects.count(), addresses + 1)
        self.assertEqual(child.client, self.acme)
        self.assertEqual(child.created_by, self.sales_person)
        self.assertEqual(child.transport_name, "Patel Roadways")
        self.assertEqual(child.contact_number, "9876543210")
        self.assertEqual(child.address.pincode.code, "394185")

    def test_names_are_stored_trimmed(self):
        child = self._resolve(
            self._new(party_name="  Shree Krishna  ", village_name=" Kamrej ")
        )
        self.assertEqual(child.party_name, "Shree Krishna")
        self.assertEqual(child.village_name, "Kamrej")

    def test_the_parents_address_link_is_reused_without_a_new_address(self):
        link = self.acme.client_addresses.get()
        addresses = Address.objects.count()
        child = self._resolve(
            {
                "party_name": "Shree Krishna",
                "village_name": "Kamrej",
                "client_address_id": link.id,
            }
        )
        self.assertEqual(child.address_id, link.address_id)
        self.assertEqual(Address.objects.count(), addresses)

    def test_a_new_child_needs_an_address(self):
        self._refused(
            {"party_name": "Shree Krishna", "village_name": "Kamrej"},
            "address or client_address_id is required",
        )
        self.assertFalse(ClientChildOrg.objects.exists())

    def test_both_address_forms_are_refused(self):
        link = self.acme.client_addresses.get()
        self._refused(self._new(client_address_id=link.id), "not both")

    def test_a_foreign_address_link_is_refused(self):
        foreign = self.rival.client_addresses.get()
        self._refused(
            {
                "party_name": "Shree Krishna",
                "village_name": "Kamrej",
                "client_address_id": foreign.id,
            },
            "one of this client's addresses",
        )

    def test_a_bad_geography_chain_is_refused(self):
        wrong_state = State.objects.exclude(pk=self.state.pk).first()
        with self.assertRaises(ValidationError):
            self._resolve(self._new(address=self._address(state=wrong_state)))
        self.assertFalse(ClientChildOrg.objects.exists())

    # -- reuse ----------------------------------------------------------------

    def test_the_same_name_and_village_reuses_the_child_whatever_the_case(self):
        first = self._resolve(self._new())
        addresses = Address.objects.count()
        again = self._resolve(
            {
                "party_name": "  SHREE KRISHNA TRADERS ",
                "village_name": "kamrej",
            }
        )
        self.assertEqual(again.pk, first.pk)
        self.assertEqual(ClientChildOrg.objects.count(), 1)
        self.assertEqual(Address.objects.count(), addresses)

    def test_resending_the_same_details_reuses_the_child(self):
        first = self._resolve(
            self._new(transport_name="Patel Roadways", contact_number="9876543210")
        )
        again = self._resolve(
            self._new(
                party_name="shree krishna traders",
                transport_name=" Patel Roadways",
                contact_number="9876543210",
            )
        )
        self.assertEqual(again.pk, first.pk)
        self.assertEqual(ClientChildOrg.objects.count(), 1)

    def test_another_client_may_use_the_same_name_and_village(self):
        first = self._resolve(self._new())
        second = self._resolve(self._new(), client=self.rival)
        self.assertNotEqual(first.pk, second.pk)

    def test_an_id_reuses_that_child(self):
        child = self._resolve(self._new())
        self.assertEqual(self._resolve({"id": child.id}).pk, child.pk)

    def test_an_id_of_another_clients_child_is_refused(self):
        child = self._resolve(self._new(), client=self.rival)
        self._refused({"id": child.id}, "No such child org for this client")

    def test_an_unknown_id_is_refused(self):
        self._refused({"id": 987654}, "No such child org for this client")

    def test_a_deleted_child_is_not_matched_and_can_be_recreated(self):
        child = self._resolve(self._new())
        child.mark_deleted(self.sales_person)
        self._refused({"id": child.id}, "No such child org for this client")
        again = self._resolve(self._new())
        self.assertNotEqual(again.pk, child.pk)

    # -- mismatches -----------------------------------------------------------

    def test_a_differing_contact_number_is_refused(self):
        self._resolve(self._new(contact_number="9876500000"))
        self._refused(
            self._new(contact_number="9876511111"),
            "contact_number: Does not match the existing child org (9876500000)",
        )

    def test_a_differing_transport_name_is_refused(self):
        self._resolve(self._new(transport_name="Patel Roadways"))
        self._refused(
            self._new(transport_name="Other Roadways"),
            "transport_name: Does not match the existing child org (Patel Roadways)",
        )

    def test_a_differing_address_is_refused(self):
        self._resolve(self._new())
        self._refused(
            self._new(address=self._address(line_1="77 Elsewhere Lane")),
            "address: Does not match the existing child org",
        )

    def test_a_differing_address_link_is_refused(self):
        self._resolve(self._new())
        link = self.acme.client_addresses.get()
        self._refused(
            {
                "party_name": "Shree Krishna Traders",
                "village_name": "Kamrej",
                "client_address_id": link.id,
            },
            "client_address_id: Does not match the existing child org",
        )

    def test_the_matching_address_link_is_accepted(self):
        link = self.acme.client_addresses.get()
        first = self._resolve(
            {
                "party_name": "Shree Krishna",
                "village_name": "Kamrej",
                "client_address_id": link.id,
            }
        )
        again = self._resolve(
            {
                "party_name": "Shree Krishna",
                "village_name": "Kamrej",
                "client_address_id": link.id,
            }
        )
        self.assertEqual(first.pk, again.pk)

    def test_fields_that_were_not_sent_are_not_compared(self):
        first = self._resolve(
            self._new(transport_name="Patel Roadways", contact_number="9876500000")
        )
        again = self._resolve(
            {"party_name": "Shree Krishna Traders", "village_name": "Kamrej"}
        )
        self.assertEqual(first.pk, again.pk)

    def test_an_id_with_a_differing_field_is_still_checked(self):
        child = self._resolve(self._new(contact_number="9876500000"))
        self._refused(
            {"id": child.id, "contact_number": "9876511111"},
            "contact_number: Does not match",
        )

    # -- payloads and picker --------------------------------------------------

    def test_payloads(self):
        child = self._resolve(
            self._new(transport_name="Patel Roadways", contact_number="9876543210")
        )
        full = child_org_payload(child)
        self.assertEqual(full["id"], child.id)
        self.assertEqual(full["party_name"], "Shree Krishna Traders")
        self.assertEqual(full["transport_name"], "Patel Roadways")
        self.assertEqual(full["contact_number"], "9876543210")
        self.assertEqual(full["address"]["pincode"], "394185")
        self.assertEqual(
            child_org_summary_payload(child),
            {"id": child.id, "party_name": "Shree Krishna Traders", "village_name": "Kamrej"},
        )
        self.assertIsNone(child_org_payload(None))
        self.assertIsNone(child_org_summary_payload(None))

    def test_the_picker_lists_live_children_of_one_client_in_order(self):
        b = self._resolve(self._new(party_name="B Traders"))
        a2 = self._resolve(self._new(party_name="A Traders", village_name="Zed"))
        a1 = self._resolve(self._new(party_name="A Traders", village_name="Alpha"))
        gone = self._resolve(self._new(party_name="C Traders"))
        gone.mark_deleted(self.sales_person)
        self._resolve(self._new(), client=self.rival)
        self.assertEqual(list(client_child_orgs(self.acme)), [a1, a2, b])

    def test_pincode_rows_are_reused(self):
        self._resolve(self._new())
        self._resolve(self._new(party_name="Other", village_name="Other"))
        self.assertEqual(Pincode.objects.filter(code="394185", city=self.city).count(), 1)
