"""Address creation and payload helpers for the ``aggregator`` master data.

Addresses are managed on the backend (Django admin) side and are not returned
by the sales_admin user APIs, but these helpers centralise the common address
operations so the views stay thin.
"""

from __future__ import annotations

from typing import Any

from aggregator.models import Address


def create_address(address_data: dict | None, actor: Any) -> Address | None:
    """Persist a validated ``aggregator.Address``, recording ``actor`` as its
    creator. Returns ``None`` when no address data is supplied.

    The full pincode/city/state/country chain is validated by ``Address.clean()``.
    """
    if not address_data:
        return None
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
