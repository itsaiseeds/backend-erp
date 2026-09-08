"""Product-packaging update/delete endpoint.

Handles ``PATCH``/``DELETE``
``/api/sales-admin/product-packagings/<public_id>``.

Only an application Admin may update or delete a packaging (``admin_required``
on ``AdminApiView``). Packagings are addressed by their ``public_id``
(``PP-…``); the ``product`` + ``packet_weight`` + ``packets`` triple is
validated for uniqueness, excluding the packaging being edited. Soft-deleted
packagings are never found (404).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import Product, ProductPackaging
from api.admin import AdminApiView
from common.models.timestamped import indian_now

from .ProductPackagingsView import ProductPackagingPayloadSerializer, packaging_payload


class UpdateProductPackagingSerializer(serializers.Serializer):
    """Request validation for updating a ``ProductPackaging`` (all fields optional)."""

    product = serializers.SlugRelatedField(
        slug_field="public_id", queryset=Product.objects.all(), required=False
    )
    packet_weight = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        required=False,
        error_messages={"invalid": "Packing packet weight must be a valid number."},
    )
    packets = serializers.IntegerField(
        min_value=1,
        required=False,
        error_messages={"min_value": "Packing packet count must be at least 1."},
    )
    selling_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=0
    )

    def validate(self, attrs):
        if self.instance is None:
            return attrs
        product = attrs.get("product", self.instance.product)
        weight = attrs.get("packet_weight", self.instance.packet_weight)
        packets = attrs.get("packets", self.instance.packets)
        if weight <= 0:
            raise serializers.ValidationError(
                "Packing packet weight must be positive."
            )
        qs = ProductPackaging.all_objects.filter(
            product=product, packet_weight=weight, packets=packets
        )
        qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "This product already has a packaging with this packet weight and packet count."
            )
        return attrs


class UpdateProductPackagingView(AdminApiView):
    """Update or delete a single product packaging (app admin only)."""

    serializer_class = UpdateProductPackagingSerializer
    admin_required = True

    @extend_schema(
        summary="Update a product packaging",
        request=UpdateProductPackagingSerializer,
        responses={200: ProductPackagingPayloadSerializer},
    )
    def patch(self, request, public_id: str):
        packaging = get_object_or_404(
            ProductPackaging.objects.select_related("product"), public_id=public_id
        )

        serializer = UpdateProductPackagingSerializer(
            instance=packaging, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        for field in ("product", "packet_weight", "packets", "selling_price"):
            if field in serializer.validated_data:
                setattr(packaging, field, serializer.validated_data[field])
        packaging.save()

        return Response(packaging_payload(packaging))

    @extend_schema(
        summary="Delete a product packaging",
        responses={204: None},
    )
    def delete(self, request, public_id: str):
        packaging = get_object_or_404(ProductPackaging.objects.all(), public_id=public_id)
        packaging.is_deleted = True
        packaging.deleted_at = indian_now()
        packaging.deleted_by = request.user
        packaging.save(
            update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
