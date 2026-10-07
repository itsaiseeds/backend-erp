"""Utility endpoint: a client's child orgs, for the booked-for picker.

``GET /api/utilities/client-children?client_public_id=`` returns the client's
child orgs (``[{id, party_name, village_name, transport_name, contact_number,
address}]``) so the order screens can offer them as ``booked_for``.

Restricted to an application Admin authenticated with the web session, and
unscoped: an admin sees every client. Soft-deleted children are excluded.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.ClientChildOrgOperations import child_org_payload, client_child_orgs
from aggregator.models import Client
from api.admin import AdminApiView
from api.client_serializers import ChildOrgPayloadSerializer


class ClientPublicIdSerializer(serializers.Serializer):
    """Validates the ``client_public_id`` query param."""

    client_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "client_public_id is required.",
            "required": "client_public_id is required.",
        },
    )


class ClientChildOrgsView(AdminApiView):
    """List a client's child orgs."""

    admin_required = True

    @extend_schema(
        summary="List a client's child orgs (booked-for picker)",
        parameters=[
            OpenApiParameter(
                "client_public_id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=True,
                description="Public id of the client, e.g. C-E79QA0E2OIHF.",
            )
        ],
        responses={200: ChildOrgPayloadSerializer(many=True)},
    )
    def get(self, request):
        params = ClientPublicIdSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        client = get_object_or_404(
            Client.objects.all(), public_id=params.validated_data["client_public_id"]
        )
        return Response([child_org_payload(child) for child in client_child_orgs(client)])
