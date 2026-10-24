"""Product-packaging update/delete endpoint.

Handles ``PATCH``/``DELETE``
``/api/sales-admin/product-packagings/<public_id>``.

Only an application Admin may update or delete a packaging (``admin_required``
on ``AdminApiView``). Packagings are addressed by their ``public_id``
(``PP-…``). Soft-deleted packagings are never found (404).

**Only the selling price and the image can be edited.** ``image`` replaces the
packaging's own picture and ``remove_image`` clears it (apps then fall back to
the product's image); sending both is a 400. A packaging's ``product``,
``packet_weight`` and ``packets`` are its shape, and nothing that uses the
packaging keeps a copy of them: order lines, challans, stock counts and the
raw-material ledger all read them live. Changing one would rewrite every
existing order's totals and every printed challan, rescale every historical
count's raw kilograms, and move reserved and dispatched bags into another
product's pool. They are therefore not fields here -- a request carrying them
is simply ignored, like any other unknown key. To change a shape, create a new
packaging and delete the old one.
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import ProductPackaging
from aggregator.ProductOperations import assert_products_usable
from api.admin import AdminApiView
from common.models.timestamped import indian_now
from common.storage import delete_image, upload_image

from .ProductPackagingsView import ProductPackagingPayloadSerializer, packaging_payload


class UpdateProductPackagingSerializer(serializers.Serializer):
    """Request validation for updating a ``ProductPackaging``: selling price and image.

    A packaging's product, packet weight and packet count are fixed once it is
    created; a request carrying them is ignored. To change them, create a new
    packaging.
    """

    selling_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=0
    )
    image = serializers.ImageField(required=False)
    remove_image = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if attrs.get("image") and attrs.get("remove_image"):
            raise serializers.ValidationError(
                "Send either image or remove_image, not both."
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
        data = serializer.validated_data
        update_fields = []
        if "selling_price" in data:
            packaging.selling_price = data["selling_price"]
            update_fields.append("selling_price")

        # Upload before saving so a failed upload leaves the row untouched; the
        # object it replaces is only removed once the new URL is committed.
        image = data.get("image")
        new_image_url = ""
        replaced_image_url = ""
        if image:
            new_image_url = upload_image(image, folder="product-packagings")
            replaced_image_url = packaging.image_url
            packaging.image_url = new_image_url
            update_fields.append("image_url")
        elif data.get("remove_image") and packaging.image_url:
            replaced_image_url = packaging.image_url
            packaging.image_url = ""
            update_fields.append("image_url")

        if update_fields:
            try:
                with transaction.atomic():
                    assert_products_usable(
                        [packaging.product_id], action="have its packaging changed"
                    )
                    packaging.save(update_fields=[*update_fields, "updated_at"])
            except Exception:
                if new_image_url:
                    delete_image(new_image_url)
                raise

        if replaced_image_url:
            delete_image(replaced_image_url)

        return Response(packaging_payload(packaging))

    @extend_schema(
        summary="Delete a product packaging",
        responses={204: None},
    )
    def delete(self, request, public_id: str):
        packaging = get_object_or_404(ProductPackaging.objects.all(), public_id=public_id)
        with transaction.atomic():
            assert_products_usable([packaging.product_id], action="have its packaging deleted")
            packaging.is_deleted = True
            packaging.deleted_at = indian_now()
            packaging.deleted_by = request.user
            packaging.save(
                update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"],
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
