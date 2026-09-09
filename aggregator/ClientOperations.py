"""Client creation, verification and link-table helpers for the ``aggregator``
sales domain. Keeps view/business logic thin, mirroring ``AddressOperations``.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from typing import TYPE_CHECKING, TypeVar

from django.core.exceptions import ValidationError
from django.db import transaction

from common.models import indian_now

from .AddressOperations import address_payload, create_address
from .models import (
    Address,
    City,
    Client,
    ClientAddress,
    ClientContact,
    ClientTransportAgency,
    Contact,
    Pincode,
    Status,
    StatusIds,
    TransportAgency,
)

if TYPE_CHECKING:
    from authentication.models import User

# The three client link tables share the same shape: a ``client`` FK, a target
# FK, an ``is_primary`` flag and soft-delete columns. The declarative helpers
# below are generic over whichever one they are handed.
LinkT = TypeVar("LinkT", ClientAddress, ClientContact, ClientTransportAgency)


def create_client(
    *,
    company_name: str,
    gst_number: str,
    actor: User,
    company_phone: str = "",
) -> Client:
    """Create a client owned by ``actor`` (a sales person), pending verification."""
    client = Client(
        company_name=company_name,
        company_phone=company_phone,
        gst_number=gst_number,
        status=Status.by_id(StatusIds.VERIFICATION_PENDING),
        created_by=actor,
    )
    client.full_clean()
    client.save()
    return client


def verify_client(client: Client, admin: User) -> Client:
    """Mark ``client`` verified, recording the acting sales admin and time."""
    client.status = Status.by_id(StatusIds.VERIFIED)
    client.verified_by = admin
    client.verified_at = indian_now()
    client.full_clean()
    client.save(update_fields=["status", "verified_by", "verified_at", "updated_at"])
    return client


def add_client_address(
    client: Client,
    address: Address,
    actor: User,
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
    contact: Contact,
    actor: User,
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
    transport_agency: TransportAgency,
    actor: User,
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
    client: Client, address: Address, actor: User
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


# --- Declarative list maintenance --------------------------------------------
#
# A client's addresses, contacts and transport agencies are maintained as whole
# lists: the caller sends the complete desired list and the helpers below
# reconcile the link rows against it. Entries are matched by their natural key
# (their content), never by an id, so "editing" a contact's phone number is an
# unlink plus a link rather than a rewrite of a ``Contact`` row that another
# client may also point at.


def _unlink(link: LinkT, actor: User) -> None:
    """Soft delete a link row.

    ``SoftDeletedModel.delete()`` is deliberately bypassed: it requires the
    Django ``delete_<model>`` permission, which a sales person does not hold,
    and these link tables are maintained by the API itself.
    """
    link.is_deleted = True
    link.deleted_at = indian_now()
    link.deleted_by = actor
    link.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])


def _primary_index(items: list[dict], label: str) -> int:
    """Position of the entry to mark primary.

    A single entry is always the primary one. With several, the caller's
    ``is_primary`` flag decides, and the first entry wins when none is flagged --
    a client must always have a primary, since the Android client list is
    grouped by the primary address's city.
    """
    flagged = [i for i, item in enumerate(items) if item.get("is_primary")]
    if len(flagged) > 1:
        raise ValidationError(f"Only one {label} can be marked primary.")
    return flagged[0] if flagged else 0


def _apply_primary(links: list[LinkT], primary_index: int) -> None:
    """Point ``is_primary`` at exactly one link.

    Demotions are saved before the promotion so the ``uniq_*_one_primary``
    partial unique indexes never see two primaries at once.
    """
    for position, link in enumerate(links):
        if link.is_primary and position != primary_index:
            link.is_primary = False
            link.save(update_fields=["is_primary", "updated_at"])
    primary = links[primary_index]
    if not primary.is_primary:
        primary.is_primary = True
        primary.save(update_fields=["is_primary", "updated_at"])


def _sync_links(
    items: list[dict],
    links: list[LinkT],
    actor: User,
    *,
    label: str,
    link_key: Callable[[LinkT], Hashable],
    item_key: Callable[[dict], Hashable],
    create: Callable[[dict], LinkT],
    update: Callable[[LinkT, dict], None],
) -> list[LinkT]:
    """Reconcile ``links`` against the submitted ``items`` (full replacement)."""
    if not items:
        raise ValidationError(f"At least one {label} is required.")

    keys = [item_key(item) for item in items]
    if len(set(keys)) != len(keys):
        raise ValidationError(f"The same {label} is listed twice.")

    existing = {link_key(link): link for link in links}
    ordered = []
    for key, item in zip(keys, items, strict=True):
        link = existing.pop(key, None)
        if link is None:
            link = create(item)
        else:
            update(link, item)
        ordered.append(link)

    for stale in existing.values():
        _unlink(stale, actor)

    _apply_primary(ordered, _primary_index(items, label))
    return ordered


def resolve_pincode(code: str, city: City, actor: User) -> Pincode:
    """The ``Pincode`` row for ``code`` under ``city``, creating it if new.

    Cities, states and countries are master data and must already exist;
    pincodes are created on demand because a sales person types them in.
    """
    pincode = Pincode.all_objects.filter(code=code, city=city).first()
    if pincode is None:
        pincode = Pincode(code=code, city=city, created_by=actor)
        pincode.full_clean()
        pincode.save()
    elif pincode.is_deleted:
        pincode.restore()
    return pincode


def resolve_contact(name: str, phone_number: str, actor: User) -> Contact:
    """The ``Contact`` row for this name and phone, creating it if new.

    Contacts are globally unique on (name, phone number), so two clients naming
    the same person share one row -- which is why the sync helpers never edit a
    contact in place.
    """
    contact = Contact.all_objects.filter(name=name, phone_number=phone_number).first()
    if contact is None:
        contact = Contact(name=name, phone_number=phone_number, created_by=actor)
        contact.full_clean()
        contact.save()
    elif contact.is_deleted:
        contact.restore()
    return contact


def _address_item_key(item: dict) -> tuple:
    return (
        item["line_1"].strip(),
        item.get("line_2", "").strip(),
        item["pincode"].strip(),
        item["city"].id,
    )


def _address_link_key(link: ClientAddress) -> tuple:
    address = link.address
    return (
        address.address_line_1,
        address.address_line_2,
        address.pincode.code,
        address.city_id,
    )


@transaction.atomic
def sync_client_addresses(client: Client, items: list[dict], actor: User) -> list[ClientAddress]:
    """Replace the client's addresses with ``items`` (at least one required)."""

    def create(item):
        address = create_address(
            {
                "line_1": item["line_1"].strip(),
                "line_2": item.get("line_2", "").strip(),
                "pincode": resolve_pincode(item["pincode"].strip(), item["city"], actor),
                "city": item["city"],
                "state": item["state"],
                "country": item["country"],
            },
            actor,
        )
        return add_client_address(
            client, address, actor, label=item.get("label", "").strip()
        )

    def update(link, item):
        label = item.get("label", "").strip()
        if link.label != label:
            link.label = label
            link.save(update_fields=["label", "updated_at"])

    return _sync_links(
        items,
        list(client.client_addresses.select_related("address", "address__pincode").all()),
        actor,
        label="address",
        link_key=_address_link_key,
        item_key=_address_item_key,
        create=create,
        update=update,
    )


@transaction.atomic
def sync_client_contacts(client: Client, items: list[dict], actor: User) -> list[ClientContact]:
    """Replace the client's contact people with ``items`` (at least one required)."""

    def create(item):
        contact = resolve_contact(
            item["name"].strip(), item["phone_number"].strip(), actor
        )
        return add_client_contact(
            client, contact, actor, role=item.get("role", "").strip()
        )

    def update(link, item):
        role = item.get("role", "").strip()
        if link.role != role:
            link.role = role
            link.save(update_fields=["role", "updated_at"])

    return _sync_links(
        items,
        list(client.client_contacts.select_related("contact").all()),
        actor,
        label="contact person",
        link_key=lambda link: (link.contact.name, link.contact.phone_number),
        item_key=lambda item: (item["name"].strip(), item["phone_number"].strip()),
        create=create,
        update=update,
    )


@transaction.atomic
def sync_client_transport_agencies(
    client: Client, items: list[dict], actor: User
) -> list[ClientTransportAgency]:
    """Replace the client's transport agencies with ``items`` (at least one required).

    Every client owns its own ``TransportAgency`` rows, so the same name may be
    used by any number of clients -- but only once within one client.
    """

    def create(item):
        agency = TransportAgency(name=item["name"].strip(), created_by=actor)
        agency.full_clean()
        agency.save()
        return add_client_transport_agency(client, agency, actor)

    def update(link, item):
        """An agency link carries nothing but its name, which is the match key."""

    return _sync_links(
        items,
        list(client.client_transport_agencies.select_related("transport_agency").all()),
        actor,
        label="transport agency",
        link_key=lambda link: link.transport_agency.name,
        item_key=lambda item: item["name"].strip(),
        create=create,
        update=update,
    )


@transaction.atomic
def create_client_with_details(
    *,
    company_name: str,
    gst_number: str,
    addresses: list[dict],
    contacts: list[dict],
    transport_agencies: list[dict],
    actor: User,
    company_phone: str = "",
) -> Client:
    """Create a pending client together with its three mandatory lists."""
    client = create_client(
        company_name=company_name,
        gst_number=gst_number,
        actor=actor,
        company_phone=company_phone,
    )
    sync_client_addresses(client, addresses, actor)
    sync_client_contacts(client, contacts, actor)
    sync_client_transport_agencies(client, transport_agencies, actor)
    return client


def update_client_core(client: Client, **fields: str) -> Client:
    """Update the core company details -- a sales admin only path.

    ``status``, ``verified_by`` and ``verified_at`` are not editable here;
    verification goes through :func:`verify_client`.
    """
    for field in ("company_name", "company_phone", "gst_number"):
        if field in fields:
            setattr(client, field, fields[field])
    client.full_clean()
    client.save()
    return client


def _primary_link(links: list[LinkT]) -> LinkT | None:
    """The primary link among already-loaded ``links`` (no extra query)."""
    return next((link for link in links if link.is_primary), None)


def client_payload(client: Client) -> dict:
    """Frontend-facing dict for a client (identified by public id, never the pk)."""
    return {
        "public_id": client.public_id,
        "company_name": client.company_name,
        "company_phone": client.company_phone,
        "gst_number": client.gst_number,
        "status": client.status.code if client.status_id else None,
        "is_verified": client.is_verified,
        "verified_at": client.verified_at,
        "verified_by": client.verified_by.name if client.verified_by else None,
        "created_by": client.created_by.name if client.created_by else None,
        "addresses": [
            {
                "label": link.label,
                "is_primary": link.is_primary,
                **address_payload(link.address),
            }
            for link in client.client_addresses.select_related(
                "address",
                "address__pincode",
                "address__city",
                "address__state",
                "address__country",
            ).all()
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


def client_list_payload(client: Client) -> dict:
    """Compact dict for the Android client list: company plus its primary rows.

    Reads the link rows off the instance so a ``prefetch_related`` in the view
    keeps this query-free.
    """
    address_link = _primary_link(list(client.client_addresses.all()))
    contact_link = _primary_link(list(client.client_contacts.all()))
    return {
        "public_id": client.public_id,
        "company_name": client.company_name,
        "company_phone": client.company_phone,
        "status": client.status.code if client.status_id else None,
        "primary_contact": (
            {
                "name": contact_link.contact.name,
                "phone_number": contact_link.contact.phone_number,
            }
            if contact_link
            else None
        ),
        "primary_address": (
            {"label": address_link.label, **address_payload(address_link.address)}
            if address_link
            else None
        ),
    }
