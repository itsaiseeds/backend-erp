from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)

_TWO_PLACES = Decimal("0.01")
_HUNDRED = Decimal("100")


class LabTestResult(models.TextChoices):
    """The lab tester's verdict. It is entered, never derived from the counts."""

    PASS = "Pass", "Pass"
    FAIL = "Fail", "Fail"


class LabTesting(
    PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel
):
    """The grow-out test of one inward raw-material lot.

    A lot has at most one of these (``InwardRawMaterial.lab_testing``): a lot
    sent back to the lab by an admin is tested again by **updating this row**,
    not by adding a second one.

    ``result`` is the lab tester's own verdict and is independent of the
    counts. It is ``NULL`` while the lot is waiting for a (re-)test, which is
    how a reverted lot keeps its last inputs for the tester to correct.

    ``genetical_impurity`` and ``grow_out_test`` are computed from the counts
    on read and never stored::

        genetical_impurity = (female_count + ot_count) / number_of_plants * 100
        grow_out_test      = 100 - genetical_impurity

    Exposed to the frontend by its ``public_id`` (``LT-…``).
    """

    public_id_prefix = "LT-"

    number_of_plants = models.PositiveIntegerField("number of plants")
    female_count = models.PositiveIntegerField("female count")
    ot_count = models.PositiveIntegerField("OT count")
    result = models.CharField(
        "result",
        max_length=4,
        choices=LabTestResult.choices,
        null=True,
        blank=True,
        help_text="Null while the lot awaits a (re-)test.",
    )
    comment = models.TextField("comment", blank=True, default="")
    tested_by = models.ForeignKey(
        "authentication.User",
        verbose_name="tested by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Whoever last submitted or edited the test.",
    )
    tested_at = models.DateTimeField("tested at", null=True, blank=True)

    class Meta:
        verbose_name = "lab testing"
        verbose_name_plural = "lab testings"
        ordering = ["-tested_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(number_of_plants__gt=0),
                name="ck_labtesting_plants_positive",
            ),
            # Keeps impurity at most 100%, so the grow-out test never goes negative.
            models.CheckConstraint(
                condition=models.Q(
                    female_count__lte=models.F("number_of_plants") - models.F("ot_count")
                ),
                name="ck_labtesting_counts_within_plants",
            ),
        ]

    def clean(self):
        super().clean()
        if self.number_of_plants is not None and self.number_of_plants <= 0:
            raise ValidationError({"number_of_plants": "Must be greater than zero."})
        if (
            self.number_of_plants is not None
            and self.female_count is not None
            and self.ot_count is not None
            and self.female_count + self.ot_count > self.number_of_plants
        ):
            raise ValidationError(
                "Female count plus OT count cannot exceed the number of plants."
            )

    @property
    def genetical_impurity(self) -> Decimal:
        """``(female + OT) / plants * 100``, to two decimals (half-up)."""
        impurity = Decimal(self.female_count + self.ot_count) / Decimal(self.number_of_plants)
        return (impurity * _HUNDRED).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    @property
    def grow_out_test(self) -> Decimal:
        """``100 - genetical impurity``, to two decimals."""
        return _HUNDRED - self.genetical_impurity

    def __str__(self):
        return f"{self.public_id}: {self.result or 'awaiting test'}"
