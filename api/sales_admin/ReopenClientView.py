"""Client re-open endpoint: ``POST /api/sales-admin/reopen-client/``.

Moves a ``CLIENT_REJECTED`` client back to ``VERIFICATION_PENDING`` so it can be
verified (or rejected again).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from aggregator.ClientOperations import client_payload, reopen_client
from aggregator.models import Client
from api.admin import AdminApiView
from api.client_serializers import ClientPayloadSerializer

from .VerifyClientView import VerifyClientSerializer


class ReopenClientView(AdminApiView):
    """Re-open a rejected client (app admin only)."""

    serializer_class = VerifyClientSerializer
    admin_required = True

    @extend_schema(
        summary="Re-open a rejected client",
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
        reopen_client(client, request.user)
        return Response(client_payload(client))
