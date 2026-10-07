"""Client child orgs ("booked for"): get-or-create at booking time and payloads.

A child org is a downstream party a client books orders on behalf of. It is
created only through booking -- there is no create/update/delete endpoint -- by
:func:`resolve_child_org`, which runs inside the caller's transaction so a child
is never left behind when the order around it fails validation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from .AddressOperations import (
    address_payload,
    assert_geo_chain_consistent,
    create_address,
)
from .ClientOperations import resolve_pincode
from .models import Address, Client, ClientAddress, ClientChildOrg

if TYPE_CHECKING:
    from authentication.models import User


def _error(field: str, message: str) -> ValidationError:
    return ValidationError({"booked_for": f"{field}: {message}"})


def _mismatch(field: str, existing: str) -> ValidationError:
    return _error(field, f"Does not match the existing child org ({existing}).")


def _find_by_name(client: Client, party_name: str, village_name: str):
    return ClientChildOrg.objects.filter(
        client=client,
        party_name__iexact=party_name,
        village_name__iexact=village_name,
    ).first()


def _address_text(address: Address) -> str:
    return ", ".join(
        part
        for part in (
            address.address_line_1,
            address.address_line_2,
            address.pincode.code,
        )
        if part
    )


def _check_matches(child: ClientChildOrg, data: Mapping[str, object]) -> None:
    """Raise if any field the caller *sent* differs from the existing ``child``."""
    if "transport_name" in data:
        sent = str(data["transport_name"] or "").strip()
        if sent != child.transport_name.strip():
            raise _mismatch("transport_name", child.transport_name)

    if "contact_number" in data:
        sent = str(data["contact_number"] or "").strip()
        if sent != (child.contact_number or "").strip():
            raise _mismatch("contact_number", child.contact_number or "")

    if data.get("client_address_id") is not None:
        link = ClientAddress.objects.filter(
            client_id=child.client_id, id=data["client_address_id"]
        ).first()
        if link is None:
            raise _error("client_address_id", "Must be one of this client's addresses.")
        if link.address_id != child.address_id:
            raise _mismatch("client_address_id", _address_text(child.address))

    address = data.get("address")
    if isinstance(address, Mapping):
        address_row = child.address
        sent_key = (
            str(address["line_1"]).strip(),
            str(address.get("line_2", "")).strip(),
            str(address["pincode"]).strip(),
            address["city"].id,
        )
        stored_key = (
            address_row.address_line_1,
            address_row.address_line_2,
            address_row.pincode.code,
            address_row.city_id,
        )
        if sent_key != stored_key:
            raise _mismatch("address", _address_text(address_row))


def _create_child(
    client: Client, data: Mapping[str, object], party_name: str, village_name: str, actor: User
) -> ClientChildOrg:
    link_id = data.get("client_address_id")
    address_data = data.get("address")
    if link_id is None and not address_data:
        raise _error("address", "address or client_address_id is required to create a child org.")
    if link_id is not None and address_data:
        raise _error("address", "Send either client_address_id or address, not both.")

    if link_id is not None:
        link = (
            ClientAddress.objects.filter(client=client, id=link_id)
            .select_related("address")
            .first()
        )
        if link is None:
            raise _error("client_address_id", "Must be one of this client's addresses.")
        address = link.address
    elif isinstance(address_data, Mapping):
        assert_geo_chain_consistent(
            address_data["city"], address_data["state"], address_data["country"]
        )
        address = create_address(
            {
                "line_1": str(address_data["line_1"]).strip(),
                "line_2": str(address_data.get("line_2", "")).strip(),
                "pincode": resolve_pincode(
                    str(address_data["pincode"]).strip(), address_data["city"], actor
                ),
                "city": address_data["city"],
                "state": address_data["state"],
                "country": address_data["country"],
            },
            actor,
        )
    else:
        raise _error("address", "address must be an object.")

    contact_number = str(data.get("contact_number") or "").strip() or None
    child = ClientChildOrg(
        client=client,
        party_name=party_name,
        village_name=village_name,
        address=address,
        transport_name=str(data.get("transport_name") or "").strip(),
        contact_number=contact_number,
        created_by=actor,
    )
    child.full_clean()
    child.save()
    return child


def resolve_child_org(client: Client, data: Mapping[str, object], actor: User) -> ClientChildOrg:
    """Get-or-create the ``client``'s child org described by ``data``.

    ``data`` is a validated ``BookedForSerializer`` dict. An ``id`` resolves
    that exact child; otherwise ``(party_name, village_name)`` is matched
    case-insensitively among the client's live children. A match must agree
    with every other field the caller sent (400 otherwise); no match creates the
    child, which needs an address.

    Must run inside the caller's ``transaction.atomic`` so a failed order never
    leaves a child behind.
    """
    child_id = data.get("id")
    if child_id is not None:
        child = (
            ClientChildOrg.objects.filter(client=client, id=child_id)
            .select_related("address", "address__pincode")
            .first()
        )
        if child is None:
            raise ValidationError({"booked_for": "No such child org for this client."})
        _check_matches(child, data)
        return child

    party_name = str(data["party_name"]).strip()
    village_name = str(data["village_name"]).strip()

    child = _find_by_name(client, party_name, village_name)
    if child is None:
        try:
            with transaction.atomic():
                return _create_child(client, data, party_name, village_name, actor)
        except IntegrityError:
            child = _find_by_name(client, party_name, village_name)
            if child is None:
                raise
    _check_matches(child, data)
    return child


def child_org_payload(child: ClientChildOrg | None) -> dict | None:
    """Full frontend-facing dict for a child org, or ``None``."""
    if child is None:
        return None
    return {
        "id": child.id,
        "party_name": child.party_name,
        "village_name": child.village_name,
        "transport_name": child.transport_name,
        "contact_number": child.contact_number,
        "address": address_payload(child.address),
    }


def child_org_summary_payload(child: ClientChildOrg | None) -> dict | None:
    """The short form list rows carry: ``{id, party_name, village_name}``."""
    if child is None:
        return None
    return {
        "id": child.id,
        "party_name": child.party_name,
        "village_name": child.village_name,
    }


def client_child_orgs(client: Client) -> QuerySet[ClientChildOrg]:
    """``client``'s live child orgs, ordered for a picker."""
    return (
        ClientChildOrg.objects.filter(client=client)
        .select_related(
            "address",
            "address__pincode",
            "address__city",
            "address__state",
            "address__country",
        )
        .order_by("party_name", "village_name")
    )
