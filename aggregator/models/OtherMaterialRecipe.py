from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)


class OtherMaterialRecipe(
    PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel
):
    """One product pack's requirement of one other material.

    ``quantity`` is the number (or weight/volume, per ``material_type.unit_type``)
    of the material that goes into one pack of the product-variant: e.g.
    ``quantity=2`` leaflets, or a ``2.000`` kg outer cover.

    ``packet_weight`` distinguishes variants of the same product that need
    different materials -- a 2 kg bag and a 4 kg bag of the same product each
    get their own recipe row (2.000 vs 4.000).

    A recipe is never edited in place: changing ``quantity`` means soft-deleting
    the old row and creating a new one, so inward entries keep referencing the
    version they were booked against.
    """

    public_id_prefix = "OMR-"

    product = models.ForeignKey(
        "aggregator.Product",
        verbose_name="product",
        on_delete=models.PROTECT,
        related_name="material_recipes",
    )
    material_type = models.ForeignKey(
        "aggregator.OtherMaterialType",
        verbose_name="material type",
        on_delete=models.PROTECT,
        related_name="recipes",
    )
    packet_weight = models.DecimalField(
        "packet weight",
        max_digits=8,
        decimal_places=3,
        help_text="Weight of the covered packet, in kilograms (the product variant).",
    )
    quantity = models.DecimalField(
        "quantity",
        max_digits=10,
        decimal_places=3,
        help_text=(
            "Multiples of the material per pack, in the material type's unit "
            "(2 leaflets, 2.000 kg cover, 5 litre)."
        ),
    )

    class Meta:
        verbose_name = "other material recipe"
        verbose_name_plural = "other material recipes"
        ordering = ["product__name", "packet_weight"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "material_type", "packet_weight"],
                name="uniq_othermaterrecipe_product_type_weight",
            ),
            models.CheckConstraint(
                condition=models.Q(packet_weight__gt=0) & models.Q(quantity__gt=0),
                name="ck_othermaterrecipe_positive",
            ),
        ]

    def __str__(self):
        return (
            f"{self.product}: {self.quantity} {self.material_type.unit_type} "
            f"{self.material_type.name} @ {self.packet_weight}kg"
        )
