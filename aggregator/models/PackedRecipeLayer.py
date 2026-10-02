from django.db import models


class PackedRecipeLayer(models.Model):
    """Packets of one count row that were packed under one recipe.

    Freezes packing-material usage at packing time, so a recipe change (delete
    old + create new) never re-values packets that are already packed. Exactly
    one of ``inventory_snapshot`` / ``loose_stock_snapshot`` is set. A NULL
    ``recipe`` means the packets were packed while the material type had no live
    recipe. When packets are unpacked, layers of a material type are consumed
    newest first by ``opened_at``; any remainder comes off the implicit
    "unlayered" packets packed before the type's first recipe.

    Invariant, per latest pool row and material type: the sum of ``packets``
    never exceeds the row's packed packets.
    """

    inventory_snapshot = models.ForeignKey(
        "aggregator.InventorySnapshot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recipe_layers",
    )
    loose_stock_snapshot = models.ForeignKey(
        "aggregator.LooseStockSnapshot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recipe_layers",
    )
    material_type = models.ForeignKey(
        "aggregator.OtherMaterialType",
        on_delete=models.PROTECT,
        related_name="+",
    )
    recipe = models.ForeignKey(
        "aggregator.OtherMaterialRecipe",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="NULL = packed while no recipe existed for this material type.",
    )
    packets = models.PositiveBigIntegerField("packets")
    opened_at = models.DateTimeField("opened at")

    class Meta:
        verbose_name = "packed recipe layer"
        verbose_name_plural = "packed recipe layers"
        ordering = ["opened_at", "id"]
        indexes = [
            models.Index(
                fields=["inventory_snapshot"],
                name="ix_packedlayer_inventory",
                condition=models.Q(inventory_snapshot__isnull=False),
            ),
            models.Index(
                fields=["loose_stock_snapshot"],
                name="ix_packedlayer_loose",
                condition=models.Q(loose_stock_snapshot__isnull=False),
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(packets__gt=0),
                name="ck_packedrecipelayer_packets_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        inventory_snapshot__isnull=False,
                        loose_stock_snapshot__isnull=True,
                    )
                    | models.Q(
                        inventory_snapshot__isnull=True,
                        loose_stock_snapshot__isnull=False,
                    )
                ),
                name="ck_packedrecipelayer_one_snapshot",
            ),
        ]

    def __str__(self):
        return f"{self.packets} packets, material {self.material_type_id}"
