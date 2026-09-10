"""Client creation endpoint: ``POST /android/api/v1/create-client``.

A sales person onboards a client from the app. The client is born
``VERIFICATION_PENDING`` and stays that way until a sales admin approves it
through ``/api/sales-admin/verify-client/`` -- nothing here can set its status,
``verified_by`` or ``verified_at``.

At least one address, one contact person and one transport agency are required;
a list with a single entry has that entry marked primary automatically.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.ClientOperations import client_payload, create_client_with_details
from aggregator.models import Client
from aggregator.validators import validate_gst_number
from android.api.base import AndroidBaseView
from api.client_serializers import ClientListsSerializer, ClientPayloadSerializer
from authentication.validators import validate_phone_number


class CreateClientSerializer(ClientListsSerializer):
    """Request validation for creating a client with its three lists."""

    company_name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Company name is required.",
            "required": "Company name is required.",
        },
    )
    company_phone = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        default="",
        validators=[validate_phone_number],
    )
    gst_number = serializers.CharField(
        max_length=15,
        validators=[validate_gst_number],
        error_messages={
            "blank": "GST number is required.",
            "required": "GST number is required.",
        },
    )

    def validate_gst_number(self, value):
        value = value.strip().upper()
        if Client.all_objects.filter(gst_number=value).exists():
            raise serializers.ValidationError(
                "A client with this GST number already exists."
            )
        return value


class CreateClientView(AndroidBaseView):
    """Create a client owned by the calling sales person."""

    serializer_class = CreateClientSerializer

    @extend_schema(
        summary="Create a client",
        request=CreateClientSerializer,
        responses={201: ClientPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        client = create_client_with_details(
            company_name=data["company_name"].strip(),
            company_phone=data["company_phone"],
            gst_number=data["gst_number"],
            addresses=data["addresses"],
            contacts=data["contacts"],
            transport_agencies=data["transport_agencies"],
            actor=request.user,
        )
        return Response(client_payload(client), status=status.HTTP_201_CREATED)
