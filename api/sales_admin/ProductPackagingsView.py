"""Product-packaging endpoint: ``GET``/``POST`` ``/api/sales-admin/product-packagings``.

Only an application Admin may view or create packagings (``admin_required`` on
``AdminApiView``, the session-only web base). Packagings are exposed to the
frontend by their ``public_id`` (``PP-…``); the primary key is never sent out.
Soft-deleted packagings are never returned.
"""

from __future__ import annotations

from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response

from aggregator.models import Product, ProductPackaging
from aggregator.ProductOperations import assert_products_usable, usability_filter
from api.admin import AdminApiView
from api.order_serializers import ProductRefSerializer


class PackagingProductRefSerializer(ProductRefSerializer):
    """The product a packaging belongs to, with whether it is currently usable."""

    is_usable = serializers.BooleanField()


class ProductPackagingPayloadSerializer(serializers.Serializer):
    """Output shape for one packaging row."""

    public_id = serializers.CharField()
    product = PackagingProductRefSerializer()
    packet_weight = serializers.DecimalField(max_digits=8, decimal_places=3)
    packets = serializers.IntegerField(min_value=1)
    total_weight = serializers.DecimalField(max_digits=11, decimal_places=3)
    selling_price = serializers.DecimalField(max_digits=12, decimal_places=2)


class CreateProductPackagingSerializer(serializers.Serializer):
    """Request validation for creating a new ``ProductPackaging``.

    ``product`` is addressed by its ``public_id`` (``P-…``). ``selling_price``
    is the whole-packaging price; when omitted it is frozen to
    ``packets * product.price_for_weight(packet_weight)`` -- the product's
    per-kilogram rate applied to one packet, times the packets in the bag (see
    ``aggregator.ProductOperations.add_packaging``).
    """

    product = serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=Product.objects.all(),
        error_messages={"required": "Product is required."},
    )
    packet_weight = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        error_messages={"required": "Packing packet weight is required."},
    )
    packets = serializers.IntegerField(
        min_value=1,
        error_messages={"required": "Packing packet count is required."},
    )
    selling_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=0
    )

    def validate(self, attrs):
        if attrs["packet_weight"] <= 0:
            raise serializers.ValidationError(
                "Packing packet weight must be positive."
            )
        qs = ProductPackaging.all_objects.filter(
            product=attrs["product"],
            packet_weight=attrs["packet_weight"],
            packets=attrs["packets"],
        )
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "This product already has a packaging with this packet weight and packet count."
            )
        return attrs


def packaging_payload(packaging):
    """Response shape for one packaging row (never exposes the primary key)."""
    return {
        "public_id": packaging.public_id,
        "product": {
            "public_id": packaging.product.public_id,
            "name": packaging.product.name,
            "is_usable": packaging.product.is_usable,
        },
        "packet_weight": packaging.packet_weight,
        "packets": packaging.packets,
        "total_weight": packaging.total_weight,
        "selling_price": packaging.selling_price,
    }


class ProductPackagingsView(AdminApiView):
    """List (GET) or create (POST) product packagings (app admin only)."""

    serializer_class = CreateProductPackagingSerializer
    admin_required = True

    @extend_schema(
        summary="List product packagings",
        description=(
            "Packagings of usable products only by default, so this list is safe to use "
            "as a dropdown. ``?is_usable=all`` (or ``false``) also returns the "
            "packagings of frozen products, for a management screen."
        ),
        parameters=[
            OpenApiParameter(
                "is_usable",
                str,
                enum=["true", "false", "all"],
                description=(
                    "Usability of the packaging's product: ``true`` (default) usable "
                    "only, ``false`` frozen only, ``all`` both."
                ),
            )
        ],
        responses={200: ProductPackagingPayloadSerializer(many=True)},
    )
    def get(self, request):
        packagings = usability_filter(
            ProductPackaging.objects.select_related("product").order_by(
                "product__name", "packet_weight"
            ),
            request.query_params.get("is_usable"),
            field="product__is_usable",
        )
        return Response([packaging_payload(p) for p in packagings])

    @extend_schema(
        summary="Create a product packaging",
        request=CreateProductPackagingSerializer,
        responses={201: ProductPackagingPayloadSerializer},
    )
    def post(self, request):
        serializer = CreateProductPackagingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        selling_price = data.get(
            "selling_price",
            data["packets"] * data["product"].price_for_weight(data["packet_weight"]),
        )
        with transaction.atomic():
            assert_products_usable([data["product"]], action="get a packaging")
            packaging = ProductPackaging.objects.create(
                product=data["product"],
                packet_weight=data["packet_weight"],
                packets=data["packets"],
                selling_price=selling_price,
                created_by=request.user,
            )
        return Response(packaging_payload(packaging), status=status.HTTP_201_CREATED)
