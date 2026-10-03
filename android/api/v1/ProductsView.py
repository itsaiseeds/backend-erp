"""Utility endpoint: every product, ``GET /android/api/v1/utilities/products``.

The whole list, not paginated, by name -- the product picker when recording a
farmer visit (``product_public_ids``). Each row carries its ``crop_id`` so the
app can narrow the picker to the crops the farmer grows. Products, not bags: a
farmer uses a seed, whatever it was packed in.

Soft-deleted products are excluded unless ``?show_deleted=true``; each row's
``is_deleted`` tells them apart. A deleted product is listed for display only:
``create-farmer-visit`` still refuses it.

A product that is not usable (``is_usable`` false) **is** listed, flagged: farmer
visits and field trips are the one place a frozen product stays visible, since a
farmer uses a seed whatever its stock state. Everywhere else the product is hidden.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Product
from android.api.base import AndroidSharedView
from common.views.paginated_date_range import query_flag

from .CropsView import SHOW_DELETED_PARAMETER


class UtilityProductSerializer(serializers.Serializer):
    """Output shape for one product row (schema only)."""

    public_id = serializers.CharField(help_text="Send this in product_public_ids.")
    name = serializers.CharField()
    crop_id = serializers.IntegerField()
    crop = serializers.CharField()
    image_url = serializers.CharField(allow_blank=True)
    is_deleted = serializers.BooleanField()
    is_usable = serializers.BooleanField(
        help_text=(
            "False when the product is frozen (no stock or booking action is available "
            "for it). It is still listed here: farmers and field trips keep seeing it."
        )
    )


class ProductsView(AndroidSharedView):
    """List every product with its crop, optionally including soft-deleted ones."""

    @extend_schema(
        summary="List every product with its crop (not paginated)",
        parameters=[SHOW_DELETED_PARAMETER],
        responses={200: UtilityProductSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        manager = Product.all_objects if query_flag(request, "show_deleted") else Product.objects
        products = manager.select_related("crop").order_by("name", "id")
        return Response(
            [
                {
                    "public_id": product.public_id,
                    "name": product.name,
                    "crop_id": product.crop_id,
                    "crop": product.crop.name,
                    "image_url": product.image_url,
                    "is_deleted": product.is_deleted,
                    "is_usable": product.is_usable,
                }
                for product in products
            ]
        )
