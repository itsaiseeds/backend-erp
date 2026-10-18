"""Client transfer endpoint: ``POST /api/sales-admin/client/transfer-client/``.

Hands clients over to another sales person -- the step taken when a sales person
leaves. The sales person is addressed by ``SalesPerson`` id (like
``sales-people/<id>``); the target must be a live sales person.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.ClientOperations import transfer_clients
from api.admin import AdminApiView
from authentication.models import SalesPerson


class TransferClientsSerializer(serializers.Serializer):
    """Request validation for a client transfer."""

    client_ids = serializers.ListField(
        child=serializers.CharField(max_length=20),
        allow_empty=False,
        error_messages={
            "empty": "Select at least one client.",
            "required": "Clients are required.",
        },
    )
    target_sales_person_id = serializers.IntegerField(
        error_messages={"required": "Target sales person is required."}
    )

    def validate_client_ids(self, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Client ids must be unique.")
        return value


class TransferClientsResponseSerializer(serializers.Serializer):
    """Output shape (schema only)."""

    transferred_count = serializers.IntegerField()
    target_sales_person_id = serializers.IntegerField()


class TransferClientsView(AdminApiView):
    """Transfer clients to another sales person (app admin only)."""

    serializer_class = TransferClientsSerializer
    admin_required = True

    @extend_schema(
        summary="Transfer clients to another sales person",
        request=TransferClientsSerializer,
        responses={200: TransferClientsResponseSerializer},
    )
    def post(self, request):
        serializer = TransferClientsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Live only (default manager): a departed sales person cannot receive clients.
        target = get_object_or_404(
            SalesPerson.objects.select_related("user"), id=data["target_sales_person_id"]
        )
        count = transfer_clients(data["client_ids"], target.user)
        return Response(
            {"transferred_count": count, "target_sales_person_id": target.id}
        )
