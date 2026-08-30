"""User creation and response-payload helpers for the user-management endpoints.

Account creation and the dict shapes returned to clients for the
``authentication`` profiles (``Admin``, ``SalesPerson``) live here so the views
stay thin. Payloads never expose internal keys (``user_id``,
``is_deleted``/``deleted_by``/``deleted_at``); admins carry no ``city`` or
``address`` and a salesperson carries only its ``city``.
"""

from __future__ import annotations

from typing import Any

import pyotp
from django.contrib.auth import get_user_model

from authentication.models import Admin, SalesPerson

User = get_user_model()

# Value sent when the backend has no data for a field yet.
PLACEHOLDER = "N/A"


def _user_ref(user) -> dict | None:
    """Compact ``{id, name}`` reference for a user FK (``None`` when absent)."""
    if user is None or user.id is None:
        return None
    return {"id": user.id, "name": user.display_name}


def _city_ref(city) -> dict:
    if city is None or city.id is None:
        return {"id": None, "name": PLACEHOLDER}
    return {"id": city.id, "name": city.name}


def create_verified_user(data: dict, actor: Any) -> Any:
    """Create a user account that is ready to log in via TOTP.

    Accounts created here are verified and carry an active TOTP secret so the
    owner can enroll an authenticator app; ``actor`` is recorded as both
    ``created_by`` and ``verified_by``.
    """
    return User.objects.create_user(
        phone_number=data["phone_number"],
        name=data["name"],
        email=data.get("email") or None,
        is_verified=True,
        created_by=actor,
        verified_by=actor,
        totp_secret=pyotp.random_base32(),
        totp_enabled=True,
    )


def admin_payload(admin: Admin) -> dict:
    """Serialize an ``Admin`` for the frontend (no city/address or audit keys)."""
    user = admin.user
    return {
        "id": admin.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "admin",
        "created_by": _user_ref(admin.created_by),
        "created_at": admin.created_at,
        "can_update_stock_count": admin.can_update_stock_count,
        "is_salesperson": getattr(user, "salesperson_profile", None) is not None,
    }


def salesperson_payload(salesperson: SalesPerson) -> dict:
    """Serialize a ``SalesPerson`` for the frontend (city only)."""
    user = salesperson.user
    return {
        "id": salesperson.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "salesperson",
        "created_by": _user_ref(salesperson.created_by),
        "created_at": salesperson.created_at,
        "city": _city_ref(salesperson.city),
    }
