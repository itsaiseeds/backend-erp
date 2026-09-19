from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class OtherMaterialUnitType(models.TextChoices):
    """Unit of measure for a material type (the interpretation of quantity).

    Rationale: some materials are counted (``leaflets``), some weighed
    (``bag_outer_cover``, ``packet_outer_cover``), and future ones may be
    measured by volume, so one Integer "number of units" can never fit all.
    """

    COUNT = "count", "count"
    KG = "kg", "kg"
    LITRE = "litre", "litre"


class OtherMaterialType(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """Master list of "other material" kinds (bag_outer_cover, leaflets, …).

    ``unit_type`` is the unit of measure for quantities of this material; a
    recipe using this type inherits it (there is no unit column on the recipe).
    Lookup master data; seeded by ``sql/dml.sql``.
    """

    name = models.CharField("name", max_length=255)
    unit_type = models.CharField(
        "unit type",
        max_length=16,
        choices=OtherMaterialUnitType.choices,
        help_text="Unit of measure for quantities of this material.",
    )

    class Meta:
        verbose_name = "other material type"
        verbose_name_plural = "other material types"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="uniq_othermatertype_name",
            ),
        ]

    def __str__(self):
        return self.name
