"""Other-material-recipe delete endpoint: ``DELETE``.

Path: ``/api/sales-admin/other-material-recipe/<public_id>``.

Recipe changes are expressed as delete-old + create-new (see
``OtherMaterialRecipesView``), so this is delete-only: there is deliberately no
``PATCH`` on a recipe. 204 on success; soft-deleted recipes are never found
(404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from aggregator.models import OtherMaterialRecipe
from api.admin import AdminApiView


class DeleteOtherMaterialRecipeView(AdminApiView):
    """Delete a single other material recipe (app admin only)."""

    admin_required = True

    @extend_schema(
        summary="Delete an other material recipe",
        responses={204: None},
    )
    def delete(self, request, public_id: str):
        recipe = get_object_or_404(OtherMaterialRecipe.objects.all(), public_id=public_id)
        recipe.mark_deleted(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
