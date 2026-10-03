"""Recipe picker: ``GET /api/sales-admin/return-order-recipes/<public_id>``.

What the admin chooses from when accepting a return with its packing materials.
For each line of the return, every recipe of that line's ``(product,
packet_weight)`` -- **including soft-deleted ones**, since stock booked against a
since-replaced recipe still counts. Each shows its public id, material type (id,
name, unit), the quantity per packet, whether it is deleted, and when it was
created and deleted.

The chosen recipes go back in ``accept-return-order`` as one flat
``recipe_public_ids`` list.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.ReturnOrderOperations import return_order_recipe_options
from api.admin import AdminApiView
from api.return_order_serializers import ReturnOrderRecipesSerializer

from .ReturnOrderTransitionView import RETURN_PUBLIC_ID_PARAMETER, return_order_queryset


class ReturnOrderRecipesView(AdminApiView):
    """List the candidate recipes per line of a return (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Recipes to book a return's packing material against, per line",
        parameters=[RETURN_PUBLIC_ID_PARAMETER],
        responses={200: ReturnOrderRecipesSerializer},
    )
    def get(self, request: Request, public_id: str) -> Response:
        ret = get_object_or_404(return_order_queryset(), public_id=public_id)
        return Response({"lines": return_order_recipe_options(ret)})
