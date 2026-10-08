"""User creation, update, and response-payload helpers for user-management endpoints.

Account creation (``create_verified_user``), update validation serializers,
and the dict shapes / swagger schemas returned to clients for the
``authentication`` profiles (``Admin``, ``SalesPerson``, ``GodownManager``,
``LabTester``) live here so the
views stay thin. Payloads never expose internal keys (``user_id``,
``is_deleted``/``deleted_by``/``deleted_at``); an admin carries no ``city``
or ``address`` and a sales person carries only its ``city``.
"""

from __future__ import annotations

import pyotp
from django.core.exceptions import PermissionDenied
from rest_framework import serializers

from aggregator.models import City
from authentication.models import Admin, GodownManager, LabTester, SalesPerson, User
from authentication.validators import validate_phone_number

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


def _is_admin_account(user) -> bool:
    """Whether the account behind a profile is an admin or superuser.

    Such a profile is a fallback of that admin: its QR and deletion belong to the
    superuser-only admin management, so clients hide both.
    """
    return bool(user.is_superuser or user.is_admin_user)


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
    share_contact = serializers.BooleanField()
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
    is_admin = serializers.BooleanField()
    totp = TotpSerializer(required=False)


class GodownManagerPayloadSerializer(serializers.Serializer):
    """Swagger schema for one godown manager row (no location, no audit keys)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.CharField(allow_null=True, required=False)
    phone_number = serializers.CharField()
    role = serializers.CharField()
    created_by = UserRefSerializer(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    is_admin = serializers.BooleanField()
    totp = TotpSerializer(required=False)


class LabTesterPayloadSerializer(serializers.Serializer):
    """Swagger schema for one lab tester row (no location, no audit keys)."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.CharField(allow_null=True, required=False)
    phone_number = serializers.CharField()
    role = serializers.CharField()
    created_by = UserRefSerializer(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    is_admin = serializers.BooleanField()
    totp = TotpSerializer(required=False)


def can_see_totp(viewer: User, target: User) -> bool:
    """Whether ``viewer`` may be shown ``target``'s authenticator QR.

    An admin's or superuser's secret is visible to a superuser, or to that
    person themselves -- never to another admin, even through the admin's
    fallback sales-person / godown-manager profile, which shares the secret.
    """
    if viewer.is_superuser or viewer.pk == target.pk:
        return True
    return not (target.is_superuser or target.is_admin_user)


def admin_payload(admin: Admin, *, include_totp: bool = False) -> dict:
    """Serialize an ``Admin`` for the frontend (no city, address or audit keys).

    When ``include_totp`` is set, the user's TOTP provisioning URI is included
    so the caller can render/re-render an enrollment QR code. ``AdminsView``
    passes this on both creation and listing.
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
        "share_contact": admin.share_contact,
    }
    if include_totp and user.totp is not None:
        payload["totp"] = {"provisioning_uri": user.totp_provisioning_uri()}
    return payload


def salesperson_payload(salesperson: SalesPerson, *, include_totp: bool = False) -> dict:
    """Serialize a ``SalesPerson`` for the frontend (city only).

    When ``include_totp`` is set, the user's TOTP provisioning URI is included
    so the caller can render/re-render an enrollment QR code. ``SalesPeopleView``
    passes this on both creation and listing.
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
        "is_admin": _is_admin_account(user),
    }
    if include_totp and user.totp is not None:
        payload["totp"] = {"provisioning_uri": user.totp_provisioning_uri()}
    return payload


def godown_manager_payload(manager: GodownManager, *, include_totp: bool = False) -> dict:
    """Serialize a ``GodownManager`` for the frontend (no location, no audit keys).

    When ``include_totp`` is set, the user's TOTP provisioning URI is included
    so the caller can render/re-render an enrollment QR code.
    """
    user = manager.user
    payload = {
        "id": manager.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "godown_manager",
        "created_by": _user_ref(manager.created_by),
        "created_at": manager.created_at,
        "is_admin": _is_admin_account(user),
    }
    if include_totp and user.totp is not None:
        payload["totp"] = {"provisioning_uri": user.totp_provisioning_uri()}
    return payload


def lab_tester_payload(tester: LabTester, *, include_totp: bool = False) -> dict:
    """Serialize a ``LabTester`` for the frontend (no location, no audit keys).

    When ``include_totp`` is set, the user's TOTP provisioning URI is included
    so the caller can render/re-render an enrollment QR code.
    """
    user = tester.user
    payload = {
        "id": tester.id,
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": "lab_tester",
        "created_by": _user_ref(tester.created_by),
        "created_at": tester.created_at,
        "is_admin": _is_admin_account(user),
    }
    if include_totp and user.totp is not None:
        payload["totp"] = {"provisioning_uri": user.totp_provisioning_uri()}
    return payload


# -- Creation helpers ---------------------------------------------------------


def create_verified_user(data: dict, actor: User) -> User:
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


def obtain_role_user(data: dict, actor: User) -> User:
    """The user a new role is granted to: the existing one for this phone, else a new one.

    A phone number that already has an account (a deleted godown manager being
    re-hired, an admin who also becomes a lab tester) gets the role added to
    that same account; ``name``/``email`` in ``data`` are then ignored. Only a
    superuser may add a role to a superuser or an admin, the same rule the
    update/delete endpoints apply. A deactivated account is reactivated and
    its TOTP secret rotated, so the authenticator entry it had before it was
    removed stays dead and a fresh QR is shown.
    """
    user = User.objects.filter(phone_number=data["phone_number"]).first()
    if user is None:
        return create_verified_user(data, actor)

    if (user.is_superuser or user.is_admin_user) and not actor.is_superuser:
        raise PermissionDenied("Only a superuser may add a role to an admin.")

    if not user.is_active:
        user.is_active = True
        if not user.is_verified or user.verified_by_id is None:
            user.is_verified = True
            user.verified_by = actor
        user.save(
            skip_full_clean=True,
            update_fields=["is_active", "is_verified", "verified_by", "updated_at"],
        )
        rotate_totp_secret(user)
    return user


def grant_role(profile_model, user: User, actor: User, *, keep_live: bool = False, **fields):
    """Give ``user`` the ``profile_model`` role, reviving a deleted profile row.

    The profile is one-to-one with the user, so a role that was removed earlier
    is restored (with ``fields`` applied) rather than inserted again. A live
    profile is a 400, unless ``keep_live`` (the fallback sales person created
    with an admin), which leaves it exactly as it is.
    """
    profile = profile_model.all_objects.filter(user=user).first()
    if profile is None:
        return profile_model.objects.create(user=user, created_by=actor, **fields)
    if not profile.is_deleted:
        if keep_live:
            return profile
        raise serializers.ValidationError(
            {"phone_number": [f"This user is already a {profile_model._meta.verbose_name}."]}
        )
    for name, value in fields.items():
        setattr(profile, name, value)
    profile.created_by = actor
    profile.restore()
    profile.save()
    return profile


def deactivate_if_roleless(user: User) -> None:
    """Deactivate ``user`` once none of its four roles is live (superusers never are).

    Re-reads the user: the reverse profile accessors cache, and the profile
    that was just soft-deleted must not still count. ``User.save`` revokes
    credentials on the ``is_active`` change.
    """
    user = User.objects.get(pk=user.pk)
    if user.is_superuser or not user.is_active:
        return
    if (
        user.is_admin_user
        or user.is_salesperson
        or user.is_godown_manager
        or user.is_lab_tester
    ):
        return
    user.is_active = False
    user.save(skip_full_clean=True, update_fields=["is_active", "updated_at"])


def rotate_totp_secret(user: User) -> None:
    """Replace ``user``'s TOTP secret so a fresh QR must be scanned.

    The new secret is active straight away (like a freshly created account), the
    replay counter and any brute-force lockout are cleared, and ``User.save``
    revokes the sessions and tokens the old secret granted -- the old
    authenticator entry stops working and the user logs in again.
    """
    user.generate_totp_secret()
    user.totp_enabled = True
    user.totp_last_counter = None
    user.failed_totp_attempts = 0
    user.totp_lockout_until = None
    user.save(
        skip_full_clean=True,
        update_fields=[
            "totp_secret",
            "totp_enabled",
            "totp_last_counter",
            "failed_totp_attempts",
            "totp_lockout_until",
            "updated_at",
        ],
    )


# -- Update validation serializers -------------------------------------------


def _phone_number_taken(value: str, own_user_id: int | None) -> bool:
    """True if the phone belongs to a *different* user than ``own_user_id``.

    Without this the uniqueness check also matches the account being updated
    itself, so a PATCH that leaves the phone unchanged always 400s.
    """
    qs = User.objects.filter(phone_number=value)
    if own_user_id is not None:
        qs = qs.exclude(id=own_user_id)
    return qs.exists()


class UpdateAdminSerializer(serializers.Serializer):
    """Request validation for updating an ``Admin`` (name/email/phone/stock flag).

    Callers pass the ``Admin`` being edited as ``instance=`` so the phone
    uniqueness check excludes that user's own row.
    """

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10, required=False, validators=[validate_phone_number]
    )
    can_update_stock_count = serializers.BooleanField(required=False)
    share_contact = serializers.BooleanField(required=False)

    def validate_phone_number(self, value):
        own_user_id = self.instance.user.id if self.instance is not None else None
        if _phone_number_taken(value, own_user_id):
            raise serializers.ValidationError("A user with this contact number already exists.")
        return value


class UpdateSalesPersonSerializer(serializers.Serializer):
    """Request validation for updating a ``SalesPerson`` (name/email/phone/city).

    Callers pass the ``SalesPerson`` being edited as ``instance=`` so the
    phone uniqueness check excludes that user's own row.
    """

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10, required=False, validators=[validate_phone_number]
    )
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False)

    def validate_phone_number(self, value):
        own_user_id = self.instance.user.id if self.instance is not None else None
        if _phone_number_taken(value, own_user_id):
            raise serializers.ValidationError("A user with this contact number already exists.")
        return value


class UpdateGodownManagerSerializer(serializers.Serializer):
    """Request validation for updating a ``GodownManager`` (name/email/phone).

    Callers pass the ``GodownManager`` being edited as ``instance=`` so the
    phone uniqueness check excludes that user's own row.
    """

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10, required=False, validators=[validate_phone_number]
    )

    def validate_phone_number(self, value):
        own_user_id = self.instance.user.id if self.instance is not None else None
        if _phone_number_taken(value, own_user_id):
            raise serializers.ValidationError("A user with this contact number already exists.")
        return value


class UpdateLabTesterSerializer(serializers.Serializer):
    """Request validation for updating a ``LabTester`` (name/email/phone).

    Callers pass the ``LabTester`` being edited as ``instance=`` so the phone
    uniqueness check excludes that user's own row.
    """

    name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        max_length=10, required=False, validators=[validate_phone_number]
    )

    def validate_phone_number(self, value):
        own_user_id = self.instance.user.id if self.instance is not None else None
        if _phone_number_taken(value, own_user_id):
            raise serializers.ValidationError("A user with this contact number already exists.")
        return value
