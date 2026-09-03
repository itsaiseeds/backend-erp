"""User creation, update, and response-payload helpers for user-management endpoints.

Account creation (``create_verified_user``), update validation serializers,
and the dict shapes / swagger schemas returned to clients for the
``authentication`` profiles (``Admin``, ``SalesPerson``) live here so the
views stay thin. Payloads never expose internal keys (``user_id``,
``is_deleted``/``deleted_by``/``deleted_at``); an admin carries no ``city``
or ``address`` and a sales person carries only its ``city``.
"""

from __future__ import annotations

from typing import Any

import pyotp
from django.contrib.auth import get_user_model
from rest_framework import serializers

from aggregator.models import City
from authentication.models import Admin, SalesPerson
from authentication.validators import validate_phone_number

User = get_user_model()


# -- Output payloads -----------------------------------------------------------


def _user_ref(user) -> dict | None:
    """Compact ``{id, name}`` reference for a user FK (``None`` when absent)."""
    if user is None or user.id is None:
        return None
    return {"id": user.id, "name": user.display_name}


def _city_ref(city) -> dict | None:
    """Compact ``{id, name}`` reference for a city (``None`` when absent)."""
    if city is None or city.id is None:
        return None
    return {"id": city.id, "name": city.name}


class UserRefSerializer(serializers.Serializer):
    """Swagger schema for a compact ``{id, name}`` user reference."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class CityRefSerializer(serializers.Serializer):
    """Swagger schema for a compact ``{id, name}`` city reference."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class TotpSerializer(serializers.Serializer):
    """Swagger schema for a user's TOTP provisioning URI (used to render a QR code)."""

    provisioning_uri = serializers.CharField()


class AdminPayloadSerializer(serializers.Serializer):
    """Swagger schema for one admin row (no city, address or audit keys)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.CharField(allow_null=True, required=False)
    phone_number = serializers.CharField()
    role = serializers.CharField()
    created_by = UserRefSerializer(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    can_update_stock_count = serializers.BooleanField()
    totp = TotpSerializer(required=False)


class SalesPersonPayloadSerializer(serializers.Serializer):
    """Swagger schema for one sales person row (city only)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.CharField(allow_null=True, required=False)
    phone_number = serializers.CharField()
    role = serializers.CharField()
    created_by = UserRefSerializer(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    city = CityRefSerializer(allow_null=True, required=False)
    totp = TotpSerializer(required=False)


def admin_payload(admin: Admin, *, include_totp: bool = False) -> dict:
    """Serialize an ``Admin`` for the frontend (no city, address or audit keys).

    When ``include_totp`` is set the freshly created user's TOTP provisioning
    URI is included so the caller can render a QR code for the new user. The
    URI is only exposed at creation time.
    """
    user = admin.user
    payload = {
        "id": admin.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "admin",
        "created_by": _user_ref(admin.created_by),
        "created_at": admin.created_at,
        "can_update_stock_count": admin.can_update_stock_count,
    }
    if include_totp and user.totp is not None:
        payload["totp"] = {"provisioning_uri": user.totp_provisioning_uri()}
    return payload


def salesperson_payload(salesperson: SalesPerson, *, include_totp: bool = False) -> dict:
    """Serialize a ``SalesPerson`` for the frontend (city only).

    When ``include_totp`` is set the freshly created user's TOTP provisioning
    URI is included so the caller can render a QR code for the new user. The
    URI is only exposed at creation time.
    """
    user = salesperson.user
    payload = {
        "id": salesperson.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "salesperson",
        "created_by": _user_ref(salesperson.created_by),
        "created_at": salesperson.created_at,
        "city": _city_ref(salesperson.city),
    }
    if include_totp and user.totp is not None:
        payload["totp"] = {"provisioning_uri": user.totp_provisioning_uri()}
    return payload


# -- Creation helpers ---------------------------------------------------------


def create_verified_user(data: dict, actor: Any) -> Any:
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


# -- Update validation serializers -------------------------------------------


class UpdateAdminSerializer(serializers.Serializer):
    """Request validation for updating an ``Admin`` (name/email/phone/stock flag)."""

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10, required=False, validators=[validate_phone_number]
    )
    can_update_stock_count = serializers.BooleanField(required=False)

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "A user with this contact number already exists."
            )
        return value


class UpdateSalesPersonSerializer(serializers.Serializer):
    """Request validation for updating a ``SalesPerson`` (name/email/phone/city)."""

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10, required=False, validators=[validate_phone_number]
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False
    )

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "A user with this contact number already exists."
            )
        return value
