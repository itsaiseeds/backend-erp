"""Product-packaging list: ``GET`` ``godown/product-packagings``.

The Android counterpart of ``api.sales_admin.ProductPackagingsView`` -- the same
rows, the same ``packaging_payload`` builder and the same ``?is_usable=`` filter,
but **read-only**: packagings are created from the web dashboard, never from the
godown floor. Godown-manager token only.

The counter needs this list: ``godown/update-bag-stock`` is keyed by packaging
``public_id``, and the default (usable products only) is exactly the set of
packagings that may be counted -- a frozen product's packagings are refused by
the count itself. Packagings are addressed by ``public_id`` (``PP-…``), never by
primary key, and soft-deleted rows are never returned.
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import ProductPackaging
from aggregator.ProductOperations import usability_filter
from android.api.base import AndroidGodownBaseView
from api.sales_admin.ProductPackagingsView import (
    ProductPackagingPayloadSerializer,
    packaging_payload,
)


class GodownProductPackagingsView(AndroidGodownBaseView):
    """List the packagings a godown manager may count (godown manager only)."""

    @extend_schema(
        operation_id="android_api_v1_godown_product_packagings_list",
        summary="List product packagings (filter by product usability)",
        description=(
            "Packagings of usable products only by default, so this list is the "
            "set of packagings ``update-bag-stock`` will accept. "
            "``?is_usable=all`` (or ``false``) also returns the packagings of "
            "frozen products, which cannot be counted."
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
    def get(self, request: Request) -> Response:
        packagings = usability_filter(
            ProductPackaging.objects.select_related("product").order_by(
                "product__name", "packet_weight"
            ),
            request.query_params.get("is_usable"),
            field="product__is_usable",
        )
        return Response([packaging_payload(packaging) for packaging in packagings])
