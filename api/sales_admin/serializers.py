"""Shared serializers and response payloads for the user-management endpoints.

A salesperson carries a single ``city`` reference and nothing else location
related (no address, no pincode). The admin payload reports the city of its
fallback salesperson; when there is no fallback, ``city`` falls back to the
``PLACEHOLDER`` dummy string (the "send api to frontend, dummy string when the
data is not there" requirement).
"""

from typing import Any

import pyotp
from django.contrib.auth import get_user_model
from rest_framework import serializers

from aggregator.models import City
from authentication.models import Admin, SalesPerson
from authentication.validators import validate_phone_number

User = get_user_model()

# Value sent when the backend has no data for a field yet.
PLACEHOLDER = "N/A"


# -- Output payloads -----------------------------------------------------------


def _user_ref(user) -> dict | None:
    """Compact ``{id, name}`` reference for a user FK (``None`` when absent)."""
    if user is None or user.id is None:
        return None
    return {"id": user.id, "name": user.display_name}


def _city_ref(city) -> dict:
    if city is None or city.id is None:
        return {"id": None, "name": PLACEHOLDER}
    return {"id": city.id, "name": city.name}


def admin_payload(admin: Admin) -> dict:
    """Serialize an ``Admin`` for the frontend, incl. fallback salesperson data."""
    user = admin.user
    fallback = getattr(user, "salesperson_profile", None)
    return {
        "id": admin.id,
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "admin",
        "is_deleted": admin.is_deleted,
        "deleted_by": _user_ref(admin.deleted_by),
        "created_by": _user_ref(admin.created_by),
        "created_at": admin.created_at,
        "can_update_stock_count": admin.can_update_stock_count,
        "is_salesperson": fallback is not None,
        "city": _city_ref(fallback.city if fallback else None),
    }


def salesperson_payload(salesperson: SalesPerson) -> dict:
    """Serialize a ``SalesPerson`` for the frontend."""
    user = salesperson.user
    return {
        "id": salesperson.id,
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "salesperson",
        "is_deleted": salesperson.is_deleted,
        "deleted_by": _user_ref(salesperson.deleted_by),
        "created_by": _user_ref(salesperson.created_by),
        "created_at": salesperson.created_at,
        "city": _city_ref(salesperson.city),
    }


# -- Input serializers ---------------------------------------------------------


class CreatePersonSerializer(serializers.Serializer):
    """Validation for the fields shared by admin and salesperson creation."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10, validators=[validate_phone_number]
    )

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "A user with this contact number already exists."
            )
        return value


class CreateAdminSerializer(CreatePersonSerializer):
    can_update_stock_count = serializers.BooleanField(default=False)
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        help_text="City for the fallback salesperson profile created with this admin.",
    )


class CreateSalesPersonSerializer(CreatePersonSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())


# -- Creation helper ------------------------------------------------------------


def create_verified_user(data: dict, actor) -> Any:
    """Create a user account that is ready to log in via TOTP.

    Accounts created here are verified, carry an active TOTP secret (so the
    owner can enroll an authenticator app), and record ``actor`` as both
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
