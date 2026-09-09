"""Client list endpoint: ``GET /api/sales-admin/get-clients/``.

Placeholder. The sales-admin client list has not been specified yet -- what an
admin should see (every client, filters, pagination) is a different question
from the Android list, which is scoped to one sales person and grouped by city.
Until then the route exists and says so.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from api.admin import AdminApiView


class GetClientsView(AdminApiView):
    """Not implemented yet (app admin only)."""

    admin_required = True

    @extend_schema(summary="List clients (work in progress)", responses={501: None})
    def get(self, request):
        return Response(
            {"detail": "Work in progress."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
