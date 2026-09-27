"""Utility endpoint: every crop, ``GET /android/api/v1/utilities/crops``.

``[{id, name, is_deleted}, ...]`` by name -- the whole list, not paginated -- so
the app can render the crop picker when recording a farmer visit
(``crop_ids``). Soft-deleted crops are excluded unless ``?show_deleted=true``;
each row's ``is_deleted`` tells them apart. A deleted crop is listed for
display only: ``create-farmer-visit`` still refuses it.

``SHOW_DELETED_PARAMETER`` is reused by ``ProductsView``.
"""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Crop
from android.api.base import AndroidBaseView
from common.views.paginated_date_range import query_flag

SHOW_DELETED_PARAMETER = OpenApiParameter(
    "show_deleted",
    OpenApiTypes.BOOL,
    description=(
        "Also return soft-deleted rows (default false; a bare ?show_deleted means "
        "true). Each row's is_deleted marks them."
    ),
)


class UtilityCropSerializer(serializers.Serializer):
    """Output shape for one crop row (schema only)."""

    id = serializers.IntegerField(help_text="Send this in crop_ids.")
    name = serializers.CharField()
    is_deleted = serializers.BooleanField()


class CropsView(AndroidBaseView):
    """List every crop, optionally including soft-deleted ones."""

    @extend_schema(
        summary="List every crop (not paginated)",
        parameters=[SHOW_DELETED_PARAMETER],
        responses={200: UtilityCropSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        manager = Crop.all_objects if query_flag(request, "show_deleted") else Crop.objects
        crops = manager.order_by("name", "id")
        return Response(
            [{"id": crop.id, "name": crop.name, "is_deleted": crop.is_deleted} for crop in crops]
        )
