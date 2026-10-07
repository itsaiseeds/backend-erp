from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)


class NonStockUnit(models.TextChoices):
    """Unit of measure for a non-stock inward entry's ``quantity``."""

    KG = "kg", "kg"
    G = "g", "g"
    LITRE = "litre", "litre"
    ML = "ml", "ml"
    COUNT = "count", "count"
    PACKET = "packet", "packet"


class NonStockInward(
    PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel
):
    """An incoming consumable that is not seed stock (pesticides, insecticides,
    spare parts, ...).

    A standalone register: deliberately linked to nothing -- no product, party,
    recipe or stock ledger -- and never counted in any stock figure. ``name``,
    ``quantity`` and ``unit`` are required; ``description``, ``company_name``
    and ``price`` are optional.

    Exposed to the frontend by its ``public_id`` (``NS-…``).
    """

    public_id_prefix = "NS-"

    name = models.CharField("name", max_length=255)
    description = models.TextField("description", blank=True, default="")
    company_name = models.CharField("company name", max_length=255, blank=True, default="")
    price = models.DecimalField(
        "price",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quantity = models.DecimalField("quantity", max_digits=10, decimal_places=3)
    unit = models.CharField(
        "unit of measure",
        max_length=16,
        choices=NonStockUnit.choices,
    )

    class Meta:
        verbose_name = "non-stock inward"
        verbose_name_plural = "non-stock inwards"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="ck_nonstockinward_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(price__isnull=True) | models.Q(price__gte=0),
                name="ck_nonstockinward_price_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(unit__in=NonStockUnit.values),
                name="ck_nonstockinward_unit",
            ),
        ]

    def __str__(self):
        return f"{self.public_id}: {self.name} {self.quantity} {self.unit}"
