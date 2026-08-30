"""Shared serializers and response payloads for the user-management endpoints.

Admins carry a full (optional) address persisted as an ``aggregator.Address``
row (line 1, line 2, pincode, city, state, country) and echoed back in the
payload. Salespeople carry only a ``city`` reference and never touch address
data. When an admin has no address, the output ``address`` block falls back to
the ``PLACEHOLDER`` dummy string (the "send api to frontend, dummy string when
the data is not there" requirement).
"""

from typing import Any

import pyotp
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from aggregator.models import Address, City, Country, Pincode, State
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


def _address_payload(address: Address | None) -> dict:
    """Full address block (admins only); ``PLACEHOLDER`` values when absent."""
    if address is None or address.id is None:
        return dict.fromkeys(
            ("line_1", "line_2", "city", "state", "pincode", "country"), PLACEHOLDER
        )
    return {
        "line_1": address.address_line_1,
        "line_2": address.address_line_2,
        "city": address.city.name,
        "state": address.state.name,
        "pincode": address.pincode.code,
        "country": address.country.name,
    }


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
        "address": _address_payload(admin.address),
    }


def salesperson_payload(salesperson: SalesPerson) -> dict:
    """Serialize a ``SalesPerson`` for the frontend (city only, no address)."""
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


class AddressInputSerializer(serializers.Serializer):
    """Validation for the optional nested ``address`` block (admins only).

    When present, every field below is required (``line_2`` defaults to an
    empty string) and the full pincode/city/state/country chain is validated
    the same way ``aggregator.Address.clean()`` does.
    """

    line_1 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False)
    state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False
    )
    pincode = serializers.PrimaryKeyRelatedField(
        queryset=Pincode.objects.all(), required=False
    )
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False
    )

    REQUIRED_FIELDS = ("line_1", "city", "state", "pincode", "country")

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Address cannot be an empty object.")
        for field in self.REQUIRED_FIELDS:
            if not attrs.get(field):
                raise serializers.ValidationError(
                    {field: "This field is required when an address is provided."}
                )
        if "line_2" not in attrs or not attrs["line_2"]:
            attrs["line_2"] = ""
        draft = Address(
            address_line_1=attrs["line_1"],
            address_line_2=attrs["line_2"],
            city=attrs["city"],
            state=attrs["state"],
            pincode=attrs["pincode"],
            country=attrs["country"],
        )
        try:
            draft.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


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
    address = AddressInputSerializer(required=False, allow_null=True)


class CreateSalesPersonSerializer(CreatePersonSerializer):
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all())


# -- Creation helpers ---------------------------------------------------------


def create_address(
    address_data: dict | None, actor: Any
) -> Address | None:
    """Persist a validated nested ``address`` block, or return ``None``.

    The data has already been validated by ``AddressInputSerializer``; this only
    constructs the row and records ``actor`` as its ``created_by``.
    """
    if not address_data:
        return None
    address = Address(
        address_line_1=address_data["line_1"],
        address_line_2=address_data["line_2"],
        city=address_data["city"],
        state=address_data["state"],
        pincode=address_data["pincode"],
        country=address_data["country"],
        created_by=actor,
    )
    address.full_clean()
    address.save()
    return address


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
