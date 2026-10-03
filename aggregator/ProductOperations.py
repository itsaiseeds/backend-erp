"""Product and packaging helpers for the ``aggregator`` sales domain.

Products and packagings are exposed to the frontend by their ``public_id``
(``P-…`` / ``PP-…``); these payloads never include the internal primary key.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet

from common.models import indian_now

from .models import (
    Crop,
    Product,
    ProductDescriptionItem,
    ProductPackaging,
    Stage,
)

if TYPE_CHECKING:
    from authentication.models import User


# -- Usability freeze ---------------------------------------------------------
#
# ``Product.is_usable = False`` freezes a product: nothing about it may be
# created or changed (inward lots, waste, packagings, recipes, counts,
# bookings), while its history stays visible. There is exactly one rule, below;
# every writer calls it first, inside its transaction. Release actions (hold,
# reject, unverify, revert a dispatch, delete an order) deliberately do not.


def assert_products_usable(
    products: Iterable[Product | int | None],
    *,
    field: str = "product",
    action: str = "be changed",
    subject: str = "it",
) -> None:
    """Raise a 400 unless every product in ``products`` is usable.

    ``products`` holds ``Product`` instances or primary keys (``None`` is
    ignored, so a nullable foreign key can be passed straight in). The rows are
    locked in pk order *before* they are read, so the switch in
    ``UpdateProductView`` -- which locks the same rows -- either lands before
    the check (and the write is refused) or after the write commits; a write
    can never slip past a freeze that is already in force. Therefore it must run
    inside ``transaction.atomic``; the stock-ledger ``recording`` blocks already
    are.

    Deleted products are checked too (``all_objects``): a frozen, then deleted,
    product stays frozen. One message names every offender so a caller fixes the
    request once.

    ``subject`` is who cannot act in the message ("so *it* cannot ..."); an order
    says "this order".

    ``ValidationError`` is what ``api.exceptions.custom_exception_handler``
    turns into a 400, keyed by ``field``.
    """
    ids = sorted(
        {
            item.pk if isinstance(item, Product) else int(item)
            for item in products
            if item is not None
        }
    )
    if not ids:
        return
    frozen = [
        product.name
        for product in Product.all_objects.select_for_update().filter(pk__in=ids).order_by("pk")
        if not product.is_usable
    ]
    if frozen:
        names = ", ".join(f"'{name}'" for name in frozen)
        noun = "Product" if len(frozen) == 1 else "Products"
        verb = "is" if len(frozen) == 1 else "are"
        raise ValidationError(
            {field: f"{noun} {names} {verb} not usable, so {subject} cannot {action}."}
        )


def usable_products() -> QuerySet[Product]:
    """Live products that are switched on -- the queryset every picker starts from."""
    return Product.objects.filter(is_usable=True)


def usability_filter(queryset: QuerySet, raw: str | None, *, field: str = "is_usable") -> QuerySet:
    """Apply a list endpoint's ``?is_usable=`` parameter to ``queryset``.

    The lists that feed a product **dropdown** (``products``,
    ``product-packagings``) must not offer a frozen product, so the default --
    parameter absent -- is *usable only*. The product management page, which has
    to show a frozen product so it can be switched back on, asks for it:

    * absent or ``true``: usable products only (the dropdown-safe default);
    * ``false``: only the frozen ones;
    * ``all``: both.

    ``field`` is the lookup to filter on (``product__is_usable`` for a packaging).
    A history record of a frozen product is unaffected -- this only narrows a
    picker, it never hides existing rows from the pages that report them.
    """
    value = (raw or "true").strip().lower()
    if value == "all":
        return queryset
    if value in ("true", "1"):
        return queryset.filter(**{field: True})
    if value in ("false", "0"):
        return queryset.filter(**{field: False})
    raise ValidationError({"is_usable": "Must be true, false or all."})


def usable_packagings() -> QuerySet[ProductPackaging]:
    """Live packagings of usable, live products."""
    return ProductPackaging.objects.filter(product__is_usable=True, product__is_deleted=False)


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


@transaction.atomic
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

    Refused (400) while the product is not usable.
    """
    assert_products_usable([product], action="get a packaging")
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


# -- Description items ------------------------------------------------------


def description_items_payload(product: Product) -> list[str]:
    """A product's feature bullets, in display order.

    A bare list of strings: that is what the app renders, and it is the same
    shape the sales-admin endpoints accept back, so the list round-trips
    unchanged. Reads off the instance, so a ``prefetch_related`` in the caller
    keeps this query-free.
    """
    return [item.text for item in product.description_items.all()]


def _retire_description_item(item: ProductDescriptionItem, actor: User) -> None:
    """Soft delete a bullet.

    ``SoftDeletedModel.delete()`` is deliberately bypassed, for the same reason
    as ``ClientOperations._unlink``: it demands the Django
    ``delete_productdescriptionitem`` permission, which the admins maintaining
    products through the API do not hold. This table is maintained by the API
    itself.
    """
    item.is_deleted = True
    item.deleted_at = indian_now()
    item.deleted_by = actor
    item.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])


@transaction.atomic
def sync_product_description_items(
    product: Product,
    texts: Sequence[str],
    actor: User,
) -> list[ProductDescriptionItem]:
    """Replace ``product``'s feature bullets with ``texts`` (full replacement).

    Declarative, like the client link lists in ``ClientOperations``: whoever
    calls this sends the whole desired list and the rows are reconciled against
    it. A bullet already on the product keeps its row (matched by its text) and
    is renumbered to its new position; a new one is created; one no longer
    listed is soft-deleted. An empty ``texts`` clears the list.

    A previously deleted bullet with the same text is restored rather than
    inserted again -- ``uniq_productdescriptionitem_product_text`` covers
    soft-deleted rows too, so a plain insert would hit the constraint.
    """
    existing = {
        item.text: item
        for item in ProductDescriptionItem.all_objects.filter(product=product)
    }
    ordered: list[ProductDescriptionItem] = []

    for sequence, text in enumerate(texts):
        item = existing.pop(text, None)
        if item is None:
            item = ProductDescriptionItem(
                product=product,
                text=text,
                sequence=sequence,
                created_by=actor,
            )
            item.full_clean()
            item.save()
        else:
            item.sequence = sequence
            item.is_deleted = False
            item.deleted_at = None
            item.deleted_by = None
            item.full_clean()
            item.save(
                update_fields=[
                    "sequence",
                    "is_deleted",
                    "deleted_at",
                    "deleted_by",
                    "updated_at",
                ]
            )
        ordered.append(item)

    for stale in existing.values():
        if not stale.is_deleted:
            _retire_description_item(stale, actor)

    return ordered


# -- Payloads ---------------------------------------------------------------


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
        "is_usable": product.is_usable,
        "description_items": description_items_payload(product),
        "packagings": [
            packaging_payload(p) for p in product.packagings.all()
        ],
    }


def catalogue_packaging_payload(packaging: ProductPackaging) -> dict:
    """One row of the Android sales-person catalogue.

    Wider than :func:`packaging_payload` -- it carries everything the app needs
    to render a product card (crop, stage, image, feature bullets) without a
    second call. Kept separate rather than widening ``packaging_payload``, which
    is embedded in every order payload and in the sales-admin API, where none of
    this belongs.
    """
    product = packaging.product
    return {
        "public_id": packaging.public_id,
        "name": str(packaging),
        "packets": packaging.packets,
        "packet_weight": str(packaging.packet_weight),
        "total_weight": str(packaging.total_weight),
        "selling_price": str(packaging.selling_price),
        "product": {
            "public_id": product.public_id,
            "name": product.name,
            "crop": product.crop.name if product.crop_id else None,
            "stage": {
                "code": product.stage.code,
                "name": product.stage.name,
                "sequence": product.stage.sequence,
            },
            "image_url": product.image_url,
            "description_items": description_items_payload(product),
        },
    }
