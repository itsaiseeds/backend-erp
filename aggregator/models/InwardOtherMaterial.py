from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)

from .InwardEntryMixin import InwardEntryMixin


class InwardOtherMaterial(
    InwardEntryMixin,
    PrefixedPublicIdModel,
    TimeStampedModel,
    SoftDeletedModel,
    CreatedByModel,
):
    """Inward movement of other (packing) materials.

    A lot of a packing material received from a ``Party``. ``quantity`` is the
    amount received, measured in the recipe's ``material_type.unit_type`` (so
    the unit comes with the recipe; only the bare number is stored here).

    Other material is usable directly -- no status, no lab gate: ``effective_date``
    is stamped with today at booking, and the entry counts toward on-hand stock
    once that date has come.

    A wrong or obsolete booking is fixed by soft-deleting the row and keying a
    fresh one against the current recipe.

    Exposed to the frontend by its ``public_id`` (``IO-…``).
    """

    public_id_prefix = "IO-"

    recipe = models.ForeignKey(
        "aggregator.OtherMaterialRecipe",
        verbose_name="recipe",
        on_delete=models.PROTECT,
        related_name="inward_entries",
    )
    quantity = models.DecimalField(
        "quantity",
        max_digits=10,
        decimal_places=3,
        help_text=(
            "Amount received from the party, in the recipe's material unit "
            "(count, kg or litre -- see recipe.material_type.unit_type)."
        ),
    )

    class Meta:
        verbose_name = "inward other material"
        verbose_name_plural = "inward other materials"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="ck_inwardothermater_quantity_positive",
            ),
        ]

    def __str__(self):
        return (
            f"{self.public_id}: {self.quantity} {self.recipe.material_type.name}"
            if self.recipe_id
            else f"inward other material {self.pk}"
        )
