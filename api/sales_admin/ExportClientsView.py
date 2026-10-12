"""Client export: ``GET /api/sales-admin/export/clients``.

Every live client, oldest first, in full -- company details, verification and
who onboarded it, every address, contact person and transport agency -- with its
child orgs ("booked for" parties) nested under ``child_orgs``.

Unlike the other exports this one has no date window: it is the client master,
not a period's activity, so ``start_date`` / ``end_date`` do not apply and the
envelope is just ``{count, results}``. Admin only.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ClientOperations import client_export_payload
from aggregator.models import Client
from api.admin import AdminApiView
from api.export_serializers import ExportClientDetailSerializer


class ExportClientsResponseSerializer(serializers.Serializer):
    """Response envelope of ``export/clients`` (schema only)."""

    count = serializers.IntegerField()
    results = ExportClientDetailSerializer(many=True)


class ExportClientsView(AdminApiView):
    """Export every client with its addresses, contacts, agencies and child orgs."""

    admin_required = True

    @extend_schema(
        operation_id="sales_admin_export_clients",
        summary="Export every client (with its child clients)",
        responses={200: ExportClientsResponseSerializer},
    )
    def get(self, request: Request, *args, **kwargs):
        clients = (
            Client.objects.select_related("status", "created_by", "verified_by")
            .prefetch_related(
                "client_addresses__address__pincode",
                "client_addresses__address__city",
                "client_addresses__address__state",
                "client_addresses__address__country",
                "client_contacts__contact",
                "client_transport_agencies__transport_agency",
                "child_orgs__address__pincode",
                "child_orgs__address__city",
                "child_orgs__address__state",
                "child_orgs__address__country",
            )
            .order_by("created_at", "id")
        )
        results = [client_export_payload(client) for client in clients]
        return Response({"count": len(results), "results": results})
