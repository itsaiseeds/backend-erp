"""Product endpoint: ``GET``/``POST`` ``/api/sales-admin/products``.

Only an application Admin may view or create products (``admin_required`` on
``AdminApiView``, the session-only web base). Products are exposed to the
frontend by their ``public_id`` (``P-…``); the primary key is never sent out.
Soft-deleted products are never returned.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import Crop, Product, ProductDescriptionItem, Stage
from aggregator.ProductOperations import (
    description_items_payload,
    sync_product_description_items,
)
from api.admin import AdminApiView
from common.storage import upload_image

# Upper bound on a product's feature list -- a marketing card, not an essay.
MAX_DESCRIPTION_ITEMS = 30


class DescriptionItemsField(serializers.ListField):
    """A product's feature bullets, in display order.

    Declared as a list of plain strings rather than nested objects on purpose:
    ``POST /api/sales-admin/products`` is ``multipart/form-data`` (it carries
    ``image``), and a list of scalars survives multipart as repeated
    ``description_items`` keys while a list of objects does not. The sequence
    each bullet is stored with is its position in the list.

    Sending the field replaces the whole list; sending ``[]`` clears it.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault(
            "child",
            serializers.CharField(
                max_length=255, allow_blank=False, trim_whitespace=True
            ),
        )
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_empty", True)
        kwargs.setdefault("max_length", MAX_DESCRIPTION_ITEMS)
        kwargs.setdefault(
            "help_text",
            "Feature bullets, in display order. Sending the list replaces it "
            "wholesale; [] clears it.",
        )
        super().__init__(**kwargs)

    def run_validation(self, data=serializers.empty):
        items = super().run_validation(data)
        if items is serializers.empty or items is None:
            return items
        seen = set()
        for text in items:
            key = text.casefold()
            if key in seen:
                raise serializers.ValidationError(
                    f"Duplicate description item: '{text}'."
                )
            seen.add(key)
        return items


def products_queryset():
    """Products with everything ``product_payload`` reads, prefetched.

    ``description_items`` would otherwise be one query per product on the list
    endpoint.
    """
    return Product.objects.select_related("crop", "stage").prefetch_related(
        Prefetch(
            "description_items",
            queryset=ProductDescriptionItem.objects.order_by("sequence", "pk"),
        )
    )


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
    description_items = serializers.ListField(child=serializers.CharField())


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
    description_items = DescriptionItemsField()

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
        "description_items": description_items_payload(product),
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
        products = products_queryset().order_by("name")
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
        # The product and its bullets go in together: a rejected bullet must not
        # leave a half-built product behind.
        with transaction.atomic():
            product = Product.objects.create(
                name=data["name"],
                crop=data["crop"],
                stage=data["stage"],
                selling_price=data["selling_price"],
                image_url=image_url,
                created_by=request.user,
            )
            sync_product_description_items(
                product, data.get("description_items", []), request.user
            )
        return Response(product_payload(product), status=status.HTTP_201_CREATED)
