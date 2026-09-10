"""Request serializers for the client lists, shared by the Android and
sales-admin client endpoints.

A client always carries at least one address, one contact person and one
transport agency. The three lists are **declarative**: whoever sends one sends
the whole desired list, and ``aggregator.ClientOperations`` reconciles the link
rows against it. That contract is identical on every endpoint, so the
serializers live here instead of being repeated in each view.
"""

from __future__ import annotations

from rest_framework import serializers

from aggregator.models import City, Country, State
from authentication.validators import validate_phone_number


class ClientAddressSerializer(serializers.Serializer):
    """One address of a client.

    City, state and country are master data and must already exist; the pincode
    is typed in by the sales person and is created on demand.
    ``Address.clean()`` then checks the whole pincode -> city -> state ->
    country chain hangs together.
    """

    line_1 = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Address line 1 is required.",
            "required": "Address line 1 is required.",
        },
    )
    line_2 = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    pincode = serializers.CharField(
        max_length=10,
        error_messages={
            "blank": "Pincode is required.",
            "required": "Pincode is required.",
        },
    )
    city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        error_messages={"required": "City is required."},
    )
    state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(),
        error_messages={"required": "State is required."},
    )
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        error_messages={"required": "Country is required."},
    )
    label = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    is_primary = serializers.BooleanField(required=False, default=False)


class ClientContactSerializer(serializers.Serializer):
    """One contact person of a client."""

    name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Contact name is required.",
            "required": "Contact name is required.",
        },
    )
    phone_number = serializers.CharField(
        max_length=10,
        validators=[validate_phone_number],
        error_messages={
            "blank": "Contact phone number is required.",
            "required": "Contact phone number is required.",
        },
    )
    role = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    is_primary = serializers.BooleanField(required=False, default=False)


class ClientTransportAgencySerializer(serializers.Serializer):
    """One transport agency of a client -- a name and nothing else."""

    name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Transport agency name is required.",
            "required": "Transport agency name is required.",
        },
    )
    is_primary = serializers.BooleanField(required=False, default=False)


class ClientListsSerializer(serializers.Serializer):
    """The three mandatory client lists.

    Subclasses redeclare a list as ``required=False`` where the endpoint allows
    it to be left untouched; the per-list rules below apply whenever a list is
    present.
    """

    addresses = ClientAddressSerializer(many=True)
    contacts = ClientContactSerializer(many=True)
    transport_agencies = ClientTransportAgencySerializer(many=True)

    def validate_addresses(self, value):
        if not value:
            raise serializers.ValidationError("At least one address is required.")
        return value

    def validate_contacts(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one contact person is required."
            )
        return value

    def validate_transport_agencies(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one transport agency is required."
            )
        names = [item["name"].strip().casefold() for item in value]
        if len(set(names)) != len(names):
            raise serializers.ValidationError(
                "A client cannot have the same transport agency twice."
            )
        return value


class ClientAddressPayloadSerializer(serializers.Serializer):
    """Output shape for one client address (schema only)."""

    label = serializers.CharField()
    is_primary = serializers.BooleanField()
    line_1 = serializers.CharField()
    line_2 = serializers.CharField()
    pincode = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()


class ClientContactPayloadSerializer(serializers.Serializer):
    """Output shape for one client contact (schema only)."""

    name = serializers.CharField()
    phone_number = serializers.CharField()
    role = serializers.CharField()
    is_primary = serializers.BooleanField()


class ClientTransportAgencyPayloadSerializer(serializers.Serializer):
    """Output shape for one client transport agency (schema only)."""

    name = serializers.CharField()
    is_primary = serializers.BooleanField()


class ClientPayloadSerializer(serializers.Serializer):
    """Output shape for a full client (schema only; responses are built by hand)."""

    public_id = serializers.CharField()
    company_name = serializers.CharField()
    company_phone = serializers.CharField()
    gst_number = serializers.CharField()
    status = serializers.CharField()
    is_verified = serializers.BooleanField()
    verified_at = serializers.DateTimeField(allow_null=True)
    verified_by = serializers.CharField(allow_null=True)
    created_by = serializers.CharField(allow_null=True)
    addresses = ClientAddressPayloadSerializer(many=True)
    contacts = ClientContactPayloadSerializer(many=True)
    transport_agencies = ClientTransportAgencyPayloadSerializer(many=True)
