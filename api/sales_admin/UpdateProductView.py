"""Product update/delete endpoint: ``PATCH``/``DELETE`` ``/api/sales-admin/products/<public_id>``.

Only an application Admin may update or delete a product (``admin_required`` on
``AdminApiView``). Products are addressed by their ``public_id`` (``P-…``);
``name`` + ``crop`` are validated for uniqueness, excluding the product being
edited. Soft-deleted products are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import Crop, Product, Stage
from api.admin import AdminApiView
from common.models.timestamped import indian_now
from common.storage import delete_image, upload_image

from .ProductsView import ProductPayloadSerializer, product_payload


class UpdateProductSerializer(serializers.Serializer):
    """Request validation for updating a ``Product`` (all fields optional)."""

    name = serializers.CharField(
        max_length=255,
        required=False,
        error_messages={"blank": "Product name may not be blank."},
    )
    crop = serializers.PrimaryKeyRelatedField(
        queryset=Crop.objects.all(), required=False
    )
    stage = serializers.PrimaryKeyRelatedField(
        queryset=Stage.objects.all(), required=False
    )
    selling_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=0,
        help_text="Rate per kilogram; packet and bag prices derive from it and the weight sold.",
    )
    image = serializers.ImageField(required=False)

    def validate(self, attrs):
        name = attrs.get("name", self.instance.name if self.instance is not None else None)
        crop = attrs.get("crop", self.instance.crop if self.instance is not None else None)
        if name is not None and crop is not None:
            name = name.strip()
            qs = Product.all_objects.filter(name=name, crop=crop)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "A product with this name and crop already exists."
                )
            attrs["name"] = name
        return attrs


class UpdateProductView(AdminApiView):
    """Update or delete a single product (app admin only)."""

    serializer_class = UpdateProductSerializer
    admin_required = True

    @extend_schema(
        summary="Update a product",
        request=UpdateProductSerializer,
        responses={200: ProductPayloadSerializer},
    )
    def patch(self, request, public_id: str):
        product = get_object_or_404(
            Product.objects.select_related("crop", "stage"), public_id=public_id
        )

        serializer = UpdateProductSerializer(
            instance=product, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        for field in ("name", "crop", "stage", "selling_price"):
            if field in serializer.validated_data:
                setattr(product, field, serializer.validated_data[field])

        # Upload before saving so a failed upload leaves the row untouched; the
        # object it replaces is only removed once the new URL is committed.
        image = serializer.validated_data.get("image")
        replaced_image_url = ""
        if image:
            replaced_image_url = product.image_url
            product.image_url = upload_image(image, folder="products")

        product.save()

        if replaced_image_url:
            delete_image(replaced_image_url)

        return Response(product_payload(product))

    @extend_schema(
        summary="Delete a product",
        responses={204: None},
    )
    def delete(self, request, public_id: str):
        product = get_object_or_404(Product.objects.all(), public_id=public_id)
        product.is_deleted = True
        product.deleted_at = indian_now()
        product.deleted_by = request.user
        product.save(
            update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
