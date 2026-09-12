"""Product endpoint: ``GET``/``POST`` ``/api/sales-admin/products``.

Only an application Admin may view or create products (``admin_required`` on
``AdminApiView``, the session-only web base). Products are exposed to the
frontend by their ``public_id`` (``P-…``); the primary key is never sent out.
Soft-deleted products are never returned.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import Crop, Product, Stage
from api.admin import AdminApiView
from common.storage import upload_image


class CropRefSerializer(serializers.Serializer):
    """Output shape for the ``crop`` reference on a product."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class StageRefSerializer(serializers.Serializer):
    """Output shape for the ``stage`` reference on a product."""

    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()


class ProductPayloadSerializer(serializers.Serializer):
    """Output shape for one product row."""

    public_id = serializers.CharField()
    name = serializers.CharField()
    crop = CropRefSerializer()
    stage = StageRefSerializer()
    selling_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Rate per kilogram; packet and bag prices derive from it and the "
            "weight sold."
        ),
    )
    image_url = serializers.CharField(allow_blank=True)


class CreateProductSerializer(serializers.Serializer):
    """Request validation for creating a new ``Product``."""

    name = serializers.CharField(
        max_length=255,
        error_messages={
            "blank": "Product name is required.",
            "required": "Product name is required.",
        },
    )
    crop = serializers.PrimaryKeyRelatedField(
        queryset=Crop.objects.all(),
        error_messages={"required": "Crop is required."},
    )
    stage = serializers.PrimaryKeyRelatedField(
        queryset=Stage.objects.all(),
        error_messages={"required": "Stage is required."},
    )
    selling_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0,
        error_messages={"required": "Selling price is required."},
        help_text="Rate per kilogram; packet and bag prices derive from it and the weight sold.",
    )
    image = serializers.ImageField(required=False)

    def validate(self, attrs):
        name = attrs["name"].strip()
        attrs["name"] = name
        qs = Product.all_objects.filter(name=name, crop=attrs["crop"])
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A product with this name and crop already exists."
            )
        return attrs


def product_payload(product):
    """Response shape for one product row (never exposes the primary key)."""
    return {
        "public_id": product.public_id,
        "name": product.name,
        "crop": {"id": product.crop_id, "name": product.crop.name},
        "stage": {
            "id": product.stage_id,
            "code": product.stage.code,
            "name": product.stage.name,
        },
        "selling_price": product.selling_price,
        "image_url": product.image_url,
    }


class ProductsView(AdminApiView):
    """List (GET) or create (POST) products (app admin only)."""

    serializer_class = CreateProductSerializer
    admin_required = True

    @extend_schema(
        summary="List products",
        responses={200: ProductPayloadSerializer(many=True)},
    )
    def get(self, request):
        products = Product.objects.select_related("crop", "stage").order_by("name")
        return Response([product_payload(product) for product in products])

    @extend_schema(
        summary="Create a product",
        request=CreateProductSerializer,
        responses={201: ProductPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Upload first: the object is named by a fresh UUID, so a failed upload
        # aborts with a 400 before any product row exists.
        image = data.get("image")
        image_url = upload_image(image, folder="products") if image else ""
        product = Product.objects.create(
            name=data["name"],
            crop=data["crop"],
            stage=data["stage"],
            selling_price=data["selling_price"],
            image_url=image_url,
            created_by=request.user,
        )
        return Response(product_payload(product), status=status.HTTP_201_CREATED)
