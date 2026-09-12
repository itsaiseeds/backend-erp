"""Client address picker: ``GET /android/api/v1/utilities/client-addresses``.

Takes a client public id and returns that client's address **links** -- one row
per ``ClientAddress``, carrying the link's own ``id`` alongside the address it
points at. That ``id`` is what
``POST /android/api/v1/create-multi-select-bag-order`` takes as
``client_address_id``: the app never handles the underlying ``Address`` row,
only the client's link to it.

Unpaginated on purpose -- a client has a handful of addresses.

Scoped to the caller: another sales person's client, or an unknown /
soft-deleted ``client_public_id``, is a 404.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.AddressOperations import address_payload
from aggregator.models import Client
from android.api.base import AndroidBaseView

CLIENT_PUBLIC_ID_PARAM = OpenApiParameter(
    "client_public_id",
    OpenApiTypes.STR,
    OpenApiParameter.QUERY,
    required=True,
    description="Public id of one of your clients, e.g. C-E79QA0E2OIHF.",
)


class ClientAddressLinkSerializer(serializers.Serializer):
    """Output shape for one client-address link (schema only)."""

    id = serializers.IntegerField(
        help_text="This link's id. Send it as client_address_id when creating an order."
    )
    label = serializers.CharField(allow_blank=True)
    is_primary = serializers.BooleanField()
    line_1 = serializers.CharField()
    line_2 = serializers.CharField(allow_blank=True)
    pincode = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    country = serializers.CharField()
    city_id = serializers.IntegerField()
    state_id = serializers.IntegerField()
    country_id = serializers.IntegerField()


class ClientPublicIdQuerySerializer(serializers.Serializer):
    """Validates the ``client_public_id`` query param."""

    client_public_id = serializers.CharField(
        max_length=20,
        error_messages={
            "blank": "client_public_id is required.",
            "required": "client_public_id is required.",
        },
    )


def client_of_caller(request: Request) -> Client:
    """The caller's client named by ``?client_public_id=``, or a 404.

    Shared by the two client-scoped link pickers, which differ only in which
    list they read off the client.
    """
    params = ClientPublicIdQuerySerializer(data=request.query_params)
    params.is_valid(raise_exception=True)
    return get_object_or_404(
        Client.objects.all(),
        public_id=params.validated_data["client_public_id"],
        created_by=request.user,
    )


def client_address_link_payload(link) -> dict:
    """One ``ClientAddress`` row, flattened with the address it points at."""
    return {
        "id": link.id,
        "label": link.label,
        "is_primary": link.is_primary,
        **address_payload(link.address),
    }


class ClientAddressesView(AndroidBaseView):
    """List one of the caller's clients' address links."""

    @extend_schema(
        operation_id="android_api_v1_utilities_client_addresses",
        summary="List a client's address links (delivery address picker)",
        parameters=[CLIENT_PUBLIC_ID_PARAM],
        responses={200: ClientAddressLinkSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        client = client_of_caller(request)
        links = client.client_addresses.select_related(
            "address",
            "address__pincode",
            "address__city",
            "address__state",
            "address__country",
        ).all()
        return Response([client_address_link_payload(link) for link in links])
