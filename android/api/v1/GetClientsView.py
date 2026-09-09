"""Client list endpoint: ``GET /android/api/v1/get-clients``.

Lists the clients the calling sales person created, grouped by the city of each
client's primary address, with that address and the primary contact person
attached so the app can render a card without a second call.

Deliberately unpaginated: ``AndroidPaginatedDateRangeListView`` returns a flat
page over a date window, which cannot express this grouping.
"""

from __future__ import annotations

from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.ClientOperations import client_list_payload
from aggregator.models import Client, ClientAddress, ClientContact
from android.api.base import AndroidBaseView
from api.client_serializers import (
    ClientAddressPayloadSerializer,
    ClientContactPayloadSerializer,
)


class ClientCityRefSerializer(serializers.Serializer):
    """Output shape for the city a group is keyed by (schema only)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class ClientListItemSerializer(serializers.Serializer):
    """Output shape for one client card (schema only)."""

    public_id = serializers.CharField()
    company_name = serializers.CharField()
    company_phone = serializers.CharField()
    status = serializers.CharField()
    primary_contact = ClientContactPayloadSerializer(allow_null=True)
    primary_address = ClientAddressPayloadSerializer(allow_null=True)


class ClientCityGroupSerializer(serializers.Serializer):
    """Output shape for one city block (schema only)."""

    city = ClientCityRefSerializer(allow_null=True)
    clients = ClientListItemSerializer(many=True)


class GetClientsView(AndroidBaseView):
    """List the calling sales person's clients, grouped by city."""

    @extend_schema(
        summary="List my clients grouped by city",
        responses={200: ClientCityGroupSerializer(many=True)},
    )
    def get(self, request):
        primary_addresses = ClientAddress.objects.filter(
            is_primary=True
        ).select_related(
            "address",
            "address__pincode",
            "address__city",
            "address__state",
            "address__country",
        )
        clients = (
            Client.objects.filter(created_by=request.user)
            .select_related("status")
            .prefetch_related(
                Prefetch("client_addresses", queryset=primary_addresses),
                Prefetch(
                    "client_contacts",
                    queryset=ClientContact.objects.filter(
                        is_primary=True
                    ).select_related("contact"),
                ),
            )
        )

        groups: dict[int | None, dict] = {}
        for client in clients:
            address_link = next(iter(client.client_addresses.all()), None)
            city = address_link.address.city if address_link else None
            group = groups.setdefault(
                city.id if city else None,
                {
                    "city": {"id": city.id, "name": city.name} if city else None,
                    "clients": [],
                },
            )
            group["clients"].append(client_list_payload(client))

        def sort_key(group):
            """Cities alphabetically; the "no primary address" block last."""
            city = group["city"]
            return (city is None, city["name"] if city else "")

        return Response(sorted(groups.values(), key=sort_key))
