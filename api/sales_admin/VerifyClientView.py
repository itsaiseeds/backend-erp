"""Client verification endpoint: ``POST /api/sales-admin/verify-client/``.

The approval step for a client a sales person onboarded from the Android app.
Marks the client ``VERIFIED`` and records the acting sales admin in
``verified_by`` / ``verified_at``. This is the only endpoint that may change a
client's status.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.ClientOperations import client_payload, verify_client
from aggregator.models import Client
from api.admin import AdminApiView
from api.client_serializers import ClientPayloadSerializer


class VerifyClientSerializer(serializers.Serializer):
    """Request validation for verifying a client."""

    public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "Client is required.",
            "required": "Client is required.",
        },
    )


class VerifyClientView(AdminApiView):
    """Approve a pending client (app admin only)."""

    serializer_class = VerifyClientSerializer
    admin_required = True

    @extend_schema(
        summary="Verify a client",
        request=VerifyClientSerializer,
        responses={200: ClientPayloadSerializer},
    )
    def post(self, request):
        serializer = VerifyClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client = get_object_or_404(
            Client.objects.select_related("status"),
            public_id=serializer.validated_data["public_id"],
        )
        if client.is_verified:
            raise serializers.ValidationError("This client is already verified.")

        verify_client(client, request.user)
        return Response(client_payload(client))
