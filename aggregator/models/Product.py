from decimal import ROUND_HALF_UP, Decimal

from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)


class Product(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A product we sell, priced per kilogram.

    ``selling_price`` is a **rate per kilogram**, not a per-packet or per-bag
    figure. Every concrete price derives from it and the weight being sold:
    ``price_for_weight(w)`` is one packet of ``w`` kg, and a bag is that times
    its ``packets``. Pricing by weight is what lets a 500g and a 1kg packet of
    the same product both prefill correctly -- notably on a
    ``CustomOrderItem``, which names a packet weight and no packaging.

    Carries a seed classification (``stage``) and an optional picture
    (``image_url``, written by ``common.storage``). Exposed to the frontend by
    its ``public_id`` (``P-…``); the primary key is never sent out.
    """

    public_id_prefix = "P-"

    name = models.CharField("name", max_length=255)
    crop = models.ForeignKey(
        "aggregator.Crop",
        verbose_name="crop",
        on_delete=models.PROTECT,
        related_name="products",
    )
    stage = models.ForeignKey(
        "aggregator.Stage",
        verbose_name="stage",
        on_delete=models.PROTECT,
        related_name="products",
    )
    selling_price = models.DecimalField(
        "selling price per kilogram",
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Rate per kilogram. Every other price derives from it and the "
            "weight being sold: a packet costs rate x packet_weight, a bag "
            "costs that x packets. Pricing by weight rather than by packet is "
            "what lets a 500g and a 1kg packet of the same product be priced "
            "correctly from one number."
        ),
    )
    image_url = models.CharField(
        "image url",
        max_length=500,
        blank=True,
        default="",
        help_text=(
            "Where the picture lives: an absolute Supabase Storage URL when "
            "deployed, a MEDIA_URL-relative path in development. Empty when no "
            "image is set. Written by common.storage.upload_image."
        ),
    )

    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "crop"],
                name="uniq_product_name_crop",
            ),
            models.CheckConstraint(
                condition=models.Q(selling_price__gte=0),
                name="ck_product_prices_non_negative",
            ),
        ]

    def price_for_weight(self, weight):
        """Price of a single packet weighing ``weight`` kilograms.

        Rounded to paise, because this is a money figure that gets stored in a
        2-decimal column (and multiplied by a packet count for a bag).
        """
        return (self.selling_price * Decimal(weight)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def __str__(self):
        return f"{self.name} ({self.crop})" if self.crop_id else self.name
