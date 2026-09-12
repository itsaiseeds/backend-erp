"""Product and packaging helpers for the ``aggregator`` sales domain.

Products and packagings are exposed to the frontend by their ``public_id``
(``P-…`` / ``PP-…``); these payloads never include the internal primary key.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Crop, Product, ProductPackaging, Stage

if TYPE_CHECKING:
    from authentication.models import User


def _resolve_crop(crop: Crop | str, actor: User) -> Crop:
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
    crop: Crop | str,
    stage: Stage,
    selling_price,
    actor: User,
    image_url: str = "",
) -> Product:
    product = Product(
        name=name,
        crop=_resolve_crop(crop, actor),
        stage=stage,
        selling_price=selling_price,
        image_url=image_url,
        created_by=actor,
    )
    product.full_clean()
    product.save()
    return product


def add_packaging(
    product: Product,
    *,
    packet_weight,
    packets: int,
    actor: User,
    selling_price=None,
) -> ProductPackaging:
    """Create a packaging for ``product``.

    ``selling_price`` is the whole-packaging price. If omitted it defaults to
    ``packets * product.price_for_weight(packet_weight)`` -- the per-kilogram
    product rate turned into a packet price, then multiplied by the packets in
    the bag (captured at creation time --
    later changes to the product's price do not propagate here).
    """
    if selling_price is None:
        selling_price = packets * product.price_for_weight(packet_weight)
    packaging = ProductPackaging(
        product=product,
        packet_weight=packet_weight,
        packets=packets,
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
        "packet_weight": str(packaging.packet_weight),
        "packets": packaging.packets,
        "total_weight": str(packaging.total_weight),
        "selling_price": str(packaging.selling_price),
    }


def product_payload(product: Product) -> dict:
    return {
        "public_id": product.public_id,
        "name": product.name,
        "crop": product.crop.name if product.crop_id else None,
        "stage": {"code": product.stage.code, "name": product.stage.name},
        "selling_price": str(product.selling_price),
        "image_url": product.image_url,
        "packagings": [
            packaging_payload(p) for p in product.packagings.all()
        ],
    }
