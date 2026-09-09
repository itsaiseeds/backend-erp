"""Client update endpoint: ``POST /api/sales-admin/update-client/``.

The admin counterpart of ``/android/api/v1/update-client``: everything a sales
person may change plus the core company details (name, phone, GST number) they
may not, on any client rather than only their own.

Status, ``verified_by`` and ``verified_at`` stay out of reach here --
verification is ``/api/sales-admin/verify-client/``'s job alone. A list left
out of the body is untouched; a list that is present replaces the stored one in
full and must keep at least one entry.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.ClientOperations import (
    client_payload,
    sync_client_addresses,
    sync_client_contacts,
    sync_client_transport_agencies,
    update_client_core,
)
from aggregator.models import Client
from aggregator.validators import validate_gst_number
from api.admin import AdminApiView
from api.client_serializers import (
    ClientAddressSerializer,
    ClientContactSerializer,
    ClientListsSerializer,
    ClientPayloadSerializer,
    ClientTransportAgencySerializer,
)
from authentication.validators import validate_phone_number

CORE_FIELDS = ("company_name", "company_phone", "gst_number")


class AdminUpdateClientSerializer(ClientListsSerializer):
    """Request validation for an admin's client update -- every field optional."""

    public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "Client is required.",
            "required": "Client is required.",
        },
    )
    company_name = serializers.CharField(
        max_length=255,
        required=False,
        error_messages={"blank": "Company name may not be blank."},
    )
    company_phone = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        validators=[validate_phone_number],
    )
    gst_number = serializers.CharField(
        max_length=15, required=False, validators=[validate_gst_number]
    )
    addresses = ClientAddressSerializer(many=True, required=False)
    contacts = ClientContactSerializer(many=True, required=False)
    transport_agencies = ClientTransportAgencySerializer(many=True, required=False)

    def validate_company_name(self, value):
        return value.strip()

    def validate_gst_number(self, value):
        # Uniqueness is left to Client.full_clean() in update_client_core, which
        # excludes the client being edited for us.
        return value.strip().upper()


class UpdateClientView(AdminApiView):
    """Update any client's core details and lists (app admin only)."""

    serializer_class = AdminUpdateClientSerializer
    admin_required = True

    @extend_schema(
        summary="Update a client",
        request=AdminUpdateClientSerializer,
        responses={200: ClientPayloadSerializer},
    )
    def post(self, request):
        serializer = AdminUpdateClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = get_object_or_404(
            Client.objects.select_related("status"), public_id=data["public_id"]
        )

        with transaction.atomic():
            core = {field: data[field] for field in CORE_FIELDS if field in data}
            if core:
                update_client_core(client, **core)
            if "addresses" in data:
                sync_client_addresses(client, data["addresses"], request.user)
            if "contacts" in data:
                sync_client_contacts(client, data["contacts"], request.user)
            if "transport_agencies" in data:
                sync_client_transport_agencies(
                    client, data["transport_agencies"], request.user
                )

        return Response(client_payload(client))
