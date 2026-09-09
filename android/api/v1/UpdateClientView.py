"""Client update endpoint: ``POST /android/api/v1/update-client``.

A sales person may only maintain the client's three lists -- addresses, contact
people and transport agencies. The core company details (name, phone, GST) and
everything about verification are a sales admin's to change
(``/api/sales-admin/update-client/``); sending one of them here is rejected
rather than silently ignored, so a mistaken app build fails loudly.

Each list is sent in full: entries missing from the list are unlinked, new ones
are added, and at least one entry must remain in every list.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.ClientOperations import (
    client_payload,
    sync_client_addresses,
    sync_client_contacts,
    sync_client_transport_agencies,
)
from aggregator.models import Client
from android.api.base import AndroidBaseView
from api.client_serializers import ClientListsSerializer, ClientPayloadSerializer

ADMIN_ONLY_FIELDS = (
    "company_name",
    "company_phone",
    "gst_number",
    "status",
    "verified_at",
    "verified_by",
)


class UpdateClientSerializer(ClientListsSerializer):
    """Request validation for a sales person's client update."""

    public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "Client is required.",
            "required": "Client is required.",
        },
    )

    def validate(self, attrs):
        sent = [field for field in ADMIN_ONLY_FIELDS if field in self.initial_data]
        if sent:
            raise serializers.ValidationError(
                "Only a sales admin can update the core client details."
            )
        return attrs


class UpdateClientView(AndroidBaseView):
    """Replace the three lists of a client the calling sales person created."""

    serializer_class = UpdateClientSerializer

    @extend_schema(
        summary="Update a client's addresses, contacts and transport agencies",
        request=UpdateClientSerializer,
        responses={200: ClientPayloadSerializer},
    )
    def post(self, request):
        serializer = UpdateClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Scoped to the caller: a sales person never sees another's clients.
        client = get_object_or_404(
            Client.objects, public_id=data["public_id"], created_by=request.user
        )

        sync_client_addresses(client, data["addresses"], request.user)
        sync_client_contacts(client, data["contacts"], request.user)
        sync_client_transport_agencies(
            client, data["transport_agencies"], request.user
        )
        return Response(client_payload(client))
