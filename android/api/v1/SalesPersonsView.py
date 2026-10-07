"""Utility endpoint: sales persons an admin can book for,
``GET /android/api/v1/utilities/sales-persons``.

Admins only (anyone else gets 403). Returns ``{id, name}`` and nothing else for
every active user with a live ``SalesPerson`` profile, the caller included. The
``id`` is what to send as ``created_by`` when booking an order and as
``sales_person_id`` on the client look-ups.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from android.api.base import AndroidSharedView
from android.api.sales_person_scope import live_sales_person_users


class SalesPersonOptionSerializer(serializers.Serializer):
    """Output shape for one bookable sales person (schema only)."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class SalesPersonsView(AndroidSharedView):
    """List the sales persons an admin may act for."""

    admin_required = True

    @extend_schema(
        summary="List sales persons an admin can book orders for (id and name only)",
        responses={200: SalesPersonOptionSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        return Response([{"id": user.id, "name": user.name} for user in live_sales_person_users()])
