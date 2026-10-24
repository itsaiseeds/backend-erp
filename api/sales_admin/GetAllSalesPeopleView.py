"""Every sales person, removed ones included: ``GET /api/sales-admin/all-sales-person/``.

The source picker for a client transfer: ``sales-people`` never lists a removed
sales person, but the clients of one who has left still need a new owner. Each
row carries ``is_deleted`` and how many live clients the person still owns, so
the admin can pick who to move clients away from, then use
``client/by-sales-person/<id>`` and ``POST client/transfer-client/``.
"""

from __future__ import annotations

from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from aggregator.models import Client
from api.admin import AdminApiView
from authentication.models import SalesPerson


class AllSalesPersonSerializer(serializers.Serializer):
    """Output shape for one sales person (schema only)."""

    id = serializers.IntegerField(help_text="SalesPerson id, as used by the other routes.")
    name = serializers.CharField()
    phone_number = serializers.CharField()
    city = serializers.CharField(allow_null=True)
    is_deleted = serializers.BooleanField()
    client_count = serializers.IntegerField(help_text="Live clients this person owns.")


class GetAllSalesPeopleView(AdminApiView):
    """List all sales people including removed ones (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="List all sales people, including removed ones",
        responses={200: AllSalesPersonSerializer(many=True)},
    )
    def get(self, request):
        owned = (
            Client.objects.filter(created_by=OuterRef("user_id"))
            .order_by()
            .values("created_by")
            .annotate(total=Count("pk"))
            .values("total")
        )
        people = (
            SalesPerson.all_objects.select_related("user", "city")
            .annotate(client_count=Coalesce(Subquery(owned, output_field=IntegerField()), 0))
            .order_by("user__name", "id")
        )
        return Response(
            [
                {
                    "id": person.id,
                    "name": person.user.name,
                    "phone_number": person.user.phone_number,
                    "city": person.city.name if person.city_id else None,
                    "is_deleted": person.is_deleted,
                    "client_count": person.client_count,
                }
                for person in people
            ]
        )
