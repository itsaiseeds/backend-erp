"""Single client detail endpoint: ``GET /android/api/v1/client/<public_id>``.

Returns one client the calling sales person created, in full: the core company
details plus every address, contact person and transport agency (each flagged
with ``is_primary``). Scoped to the caller -- another sales person's client, or
an unknown / soft-deleted ``public_id``, is a 404.

This is the detail counterpart of ``GET /android/api/v1/get-clients`` (which
returns the compact, primary-only card per client).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ClientOperations import client_payload
from aggregator.models import Client
from android.api.base import AndroidBaseView
from api.client_serializers import ClientPayloadSerializer

_PUBLIC_ID_PARAM = OpenApiParameter(
    "public_id",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="The client's public id, e.g. C-E79QA0E2OIHF.",
)


class GetClientView(AndroidBaseView):
    """Full detail of one of the caller's clients, by ``public_id``."""

    @extend_schema(
        summary="Get one of my clients in full (core + all addresses/contacts/agencies)",
        parameters=[_PUBLIC_ID_PARAM],
        responses={200: ClientPayloadSerializer},
    )
    def get(self, request: Request, public_id: str) -> Response:
        client = get_object_or_404(
            Client.objects.select_related("status", "verified_by", "created_by"),
            public_id=public_id,
            created_by=request.user,
        )
        return Response(client_payload(client))
