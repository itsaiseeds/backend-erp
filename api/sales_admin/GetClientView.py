"""Single client detail endpoint: ``GET /api/sales-admin/client/<public_id>``.

The sales-admin counterpart of ``GET /android/api/v1/client/<public_id>``:
returns one client in full -- core company details plus every address, contact
person and transport agency (each flagged with ``is_primary``). An admin may
read **any** client (not only ones they created), so this is scoped by nothing
but the ``public_id``; an unknown or soft-deleted id is a 404.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ClientOperations import client_payload
from aggregator.models import Client
from api.admin import AdminApiView
from api.client_serializers import ClientPayloadSerializer


class GetClientView(AdminApiView):
    """Full detail of one client, by ``public_id`` (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Get a client in full (core + all addresses/contacts/agencies)",
        parameters=[
            OpenApiParameter(
                "public_id",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description="The client's public id, e.g. C-E79QA0E2OIHF.",
            )
        ],
        responses={200: ClientPayloadSerializer},
    )
    def get(self, request: Request, public_id: str) -> Response:
        client = get_object_or_404(
            Client.objects.select_related("status", "verified_by", "created_by"),
            public_id=public_id,
        )
        return Response(client_payload(client))
