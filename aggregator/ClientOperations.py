"""Client creation, verification and link-table helpers for the ``aggregator``
sales domain. Keeps view/business logic thin, mirroring ``AddressOperations``.
"""

from __future__ import annotations

from typing import Any

from common.models import indian_now

from .models import (
    Client,
    ClientAddress,
    ClientContact,
    ClientTransportAgency,
    Status,
)


def _status(code: str) -> Status:
    return Status.objects.get(code=code)


def create_client(
    *,
    company_name: str,
    gst_number: str,
    actor: Any,
    company_phone: str = "",
) -> Client:
    """Create a client owned by ``actor`` (a sales person), pending verification."""
    client = Client(
        company_name=company_name,
        company_phone=company_phone,
        gst_number=gst_number,
        status=_status("VERIFICATION_PENDING"),
        created_by=actor,
    )
    client.full_clean()
    client.save()
    return client


def verify_client(client: Client, admin: Any) -> Client:
    """Mark ``client`` verified, recording the acting sales admin and time."""
    client.status = _status("VERIFIED")
    client.verified_by = admin
    client.verified_at = indian_now()
    client.full_clean()
    client.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
    return client


def add_client_address(
    client: Client,
    address: Any,
    actor: Any,
    *,
    label: str = "",
    is_primary: bool = False,
) -> ClientAddress:
    link = ClientAddress(
        client=client,
        address=address,
        label=label,
        is_primary=is_primary,
        created_by=actor,
    )
    link.full_clean()
    link.save()
    return link


def add_client_contact(
    client: Client,
    contact: Any,
    actor: Any,
    *,
    role: str = "",
    is_primary: bool = False,
) -> ClientContact:
    link = ClientContact(
        client=client,
        contact=contact,
        role=role,
        is_primary=is_primary,
        created_by=actor,
    )
    link.full_clean()
    link.save()
    return link


def add_client_transport_agency(
    client: Client,
    transport_agency: Any,
    actor: Any,
    *,
    is_primary: bool = False,
) -> ClientTransportAgency:
    link = ClientTransportAgency(
        client=client,
        transport_agency=transport_agency,
        is_primary=is_primary,
        created_by=actor,
    )
    link.full_clean()
    link.save()
    return link


def set_or_update_primary_address(
    client: Client, address: Any, actor: Any
) -> ClientAddress:
    """Make ``address`` the client's single primary address.

    Any existing primary is demoted first, so the client always has at most one
    primary address (also guarded by the ``uniq_clientaddress_one_primary``
    partial unique index).
    """
    client.client_addresses.filter(is_primary=True).exclude(address=address).update(
        is_primary=False
    )
    link, _ = ClientAddress.objects.get_or_create(
        client=client,
        address=address,
        defaults={"created_by": actor},
    )
    link.is_primary = True
    link.full_clean()
    link.save(update_fields=["is_primary", "updated_at"])
    return link


def client_payload(client: Client) -> dict:
    """Frontend-facing dict for a client (identified by GST, never internal ids)."""
    return {
        "company_name": client.company_name,
        "company_phone": client.company_phone,
        "gst_number": client.gst_number,
        "status": client.status.code if client.status_id else None,
        "is_verified": client.is_verified,
        "addresses": [
            {
                "label": link.label,
                "is_primary": link.is_primary,
                "address": str(link.address),
            }
            for link in client.client_addresses.select_related("address").all()
        ],
        "contacts": [
            {
                "name": link.contact.name,
                "phone_number": link.contact.phone_number,
                "role": link.role,
                "is_primary": link.is_primary,
            }
            for link in client.client_contacts.select_related("contact").all()
        ],
        "transport_agencies": [
            {"name": link.transport_agency.name, "is_primary": link.is_primary}
            for link in client.client_transport_agencies.select_related(
                "transport_agency"
            ).all()
        ],
    }
