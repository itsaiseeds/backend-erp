"""User creation and response-payload helpers for the user-management endpoints.

Account creation (``create_verified_user``) and the dict shapes / swagger
schemas returned to clients for the ``authentication`` profiles (``Admin``,
``SalesPerson``) live here so the views stay thin. Payloads never expose
internal keys (``user_id``, ``is_deleted``/``deleted_by``/``deleted_at``); an
admin carries no ``city`` or ``address`` and a sales person carries only its
``city``.
"""

from __future__ import annotations

from typing import Any

import pyotp
from django.contrib.auth import get_user_model
from rest_framework import serializers

from authentication.models import Admin, SalesPerson

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


def admin_payload(admin: Admin) -> dict:
    """Serialize an ``Admin`` for the frontend (no city, address or audit keys)."""
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
