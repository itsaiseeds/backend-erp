"""Product and packaging helpers for the ``aggregator`` sales domain.

Products and packagings are exposed to the frontend by their ``public_id``
(``P-…`` / ``PP-…``); these payloads never include the internal primary key.
"""

from __future__ import annotations

from typing import Any

from .models import Crop, Product, ProductPackaging


def _resolve_crop(crop: Any, actor: Any) -> Crop:
    """Accept a ``Crop`` instance or a crop name, creating the crop if needed."""
    if isinstance(crop, Crop):
        return crop
    obj, created = Crop.objects.get_or_create(
        name=crop,
        defaults={"created_by": actor},
    )
    return obj


def create_product(
    *,
    name: str,
    crop: Any,
    buying_price,
    selling_price,
    actor: Any,
) -> Product:
    product = Product(
        name=name,
        crop=_resolve_crop(crop, actor),
        buying_price=buying_price,
        selling_price=selling_price,
        created_by=actor,
    )
    product.full_clean()
    product.save()
    return product


def add_packaging(
    product: Product,
    *,
    packing_bag_weight,
    packing_bags: int,
    actor: Any,
    selling_price=None,
) -> ProductPackaging:
    """Create a packaging for ``product``.

    ``selling_price`` is the whole-packaging price. If omitted it defaults to
    ``packing_bags * product.selling_price`` (captured at creation time --
    later changes to the product's price do not propagate here).
    """
    if selling_price is None:
        selling_price = packing_bags * product.selling_price
    packaging = ProductPackaging(
        product=product,
        packing_bag_weight=packing_bag_weight,
        packing_bags=packing_bags,
        selling_price=selling_price,
        created_by=actor,
    )
    packaging.full_clean()
    packaging.save()
    return packaging


def packaging_payload(packaging: ProductPackaging) -> dict:
    return {
        "public_id": packaging.public_id,
        "product": {
            "public_id": packaging.product.public_id,
            "name": packaging.product.name,
        },
        "packing_bag_weight": str(packaging.packing_bag_weight),
        "packing_bags": packaging.packing_bags,
        "total_weight": str(packaging.total_weight),
        "selling_price": str(packaging.selling_price),
    }


def product_payload(product: Product) -> dict:
    return {
        "public_id": product.public_id,
        "name": product.name,
        "crop": product.crop.name if product.crop_id else None,
        "buying_price": str(product.buying_price),
        "selling_price": str(product.selling_price),
        "margin_per_bag": str(product.margin_per_bag),
        "packagings": [
            packaging_payload(p) for p in product.packagings.all()
        ],
    }
