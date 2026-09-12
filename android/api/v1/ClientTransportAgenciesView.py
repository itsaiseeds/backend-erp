"""Transport agency picker:
``GET /android/api/v1/utilities/client-transport-agencies``.

Takes a client public id and returns that client's transport-agency **links** --
one row per ``ClientTransportAgency``, carrying the link's own ``id`` alongside
the agency it points at. That ``id`` is what
``POST /android/api/v1/create-multi-select-bag-order`` takes as
``client_transport_agency_id``; leaving it out books a private (own-vehicle)
dispatch.

Unpaginated on purpose -- a client has a handful of agencies.

Scoped to the caller: another sales person's client, or an unknown /
soft-deleted ``client_public_id``, is a 404.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from android.api.base import AndroidBaseView

from .ClientAddressesView import CLIENT_PUBLIC_ID_PARAM, client_of_caller


class ClientTransportAgencyLinkSerializer(serializers.Serializer):
    """Output shape for one client-transport-agency link (schema only)."""

    id = serializers.IntegerField(
        help_text=(
            "This link's id. Send it as client_transport_agency_id when "
            "creating an order."
        )
    )
    name = serializers.CharField()
    is_primary = serializers.BooleanField()


def client_transport_agency_link_payload(link) -> dict:
    """One ``ClientTransportAgency`` row, flattened with its agency's name."""
    return {
        "id": link.id,
        "name": link.transport_agency.name,
        "is_primary": link.is_primary,
    }


class ClientTransportAgenciesView(AndroidBaseView):
    """List one of the caller's clients' transport-agency links."""

    @extend_schema(
        operation_id="android_api_v1_utilities_client_transport_agencies",
        summary="List a client's transport agency links (carrier picker)",
        parameters=[CLIENT_PUBLIC_ID_PARAM],
        responses={200: ClientTransportAgencyLinkSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        client = client_of_caller(request)
        links = client.client_transport_agencies.select_related(
            "transport_agency"
        ).all()
        return Response(
            [client_transport_agency_link_payload(link) for link in links]
        )
