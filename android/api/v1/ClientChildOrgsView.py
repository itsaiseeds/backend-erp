"""Client child-org picker: ``GET /android/api/v1/utilities/client-children``.

Takes a client public id and returns that client's child orgs -- the parties it
books orders on behalf of -- so the booking screen can offer them as the
``booked_for`` choice on ``POST /android/api/v1/create-multi-select-bag-order``.
A child is created through that booking itself, never here.

Unpaginated, and scoped to the caller exactly like
``utilities/client-addresses``: another sales person's client, or an unknown
``client_public_id``, is a 404.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ClientChildOrgOperations import child_org_payload, client_child_orgs
from android.api.base import AndroidSharedView
from api.client_serializers import ChildOrgPayloadSerializer

from .ClientAddressesView import (
    CLIENT_PUBLIC_ID_PARAM,
    SALES_PERSON_ID_PARAM,
    client_of_caller,
)


class ClientChildOrgsView(AndroidSharedView):
    """List one of the caller's clients' child orgs."""

    @extend_schema(
        operation_id="android_api_v1_utilities_client_children",
        summary="List a client's child orgs (booked-for picker)",
        parameters=[CLIENT_PUBLIC_ID_PARAM, SALES_PERSON_ID_PARAM],
        responses={200: ChildOrgPayloadSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        client = client_of_caller(request)
        return Response([child_org_payload(child) for child in client_child_orgs(client)])
