"""Address creation and payload helpers for the ``aggregator`` master data.

Addresses are managed on the backend (Django admin) side and are not returned
by the sales_admin user APIs, but these helpers centralise the common address
operations so the views stay thin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError

from aggregator.models import Address, City, Country, State

if TYPE_CHECKING:
    from authentication.models import User


def assert_geo_chain_consistent(city: City, state: State, country: Country) -> None:
    """Reject a city / state / country trio that does not nest.

    Picking Hyderabad with state Gujarat is a 400 here. ``Address.clean()``
    enforces the same rule at ``full_clean()`` time, but the declarative
    ``sync_client_addresses`` path matches an unchanged address by (line,
    pincode, city) and would otherwise silently drop a bad ``state`` /
    ``country`` in the payload -- so callers on that path check up front.
    """
    errors = {}
    if city.state_id != state.pk:
        errors["state"] = f"{city.name} is not a city of {state.name}."
    if state.country_id != country.pk:
        errors["country"] = f"{state.name} is not a state of {country.name}."
    if errors:
        raise ValidationError(errors)


def create_address(address_data: dict | None, actor: User) -> Address | None:
    """Persist a validated ``aggregator.Address``, recording ``actor`` as its
    creator. Returns ``None`` when no address data is supplied.

    The full pincode/city/state/country chain is validated by
    :func:`assert_geo_chain_consistent` and then ``Address.clean()``.
    """
    if not address_data:
        return None
    assert_geo_chain_consistent(
        address_data["city"], address_data["state"], address_data["country"]
    )
    address = Address(
        address_line_1=address_data["line_1"],
        address_line_2=address_data.get("line_2", ""),
        pincode=address_data["pincode"],
        city=address_data["city"],
        state=address_data["state"],
        country=address_data["country"],
        created_by=actor,
    )
    address.full_clean()
    address.save()
    return address


def address_payload(address: Address) -> dict:
    """Frontend-facing dict for an address, field by field.

    The geographic chain is spelled out (rather than collapsed into ``str()``)
    so a client can lay the address out itself.
    """
    return {
        "line_1": address.address_line_1,
        "line_2": address.address_line_2,
        "pincode": address.pincode.code,
        "city": address.city.name,
        "state": address.state.name,
        "country": address.country.name,
        "city_id": address.city_id,
        "state_id": address.state_id,
        "country_id": address.country_id,
    }
