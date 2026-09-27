from django.db import models

from authentication.validators import validate_phone_number
from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)


class FarmerVisit(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """One farmer a sales person met on a ``FieldTrip``.

    A visit, not a farmer master record: the same farmer met on two trips is
    two rows. The crops they grow are ``FarmerVisitCrop`` rows; the products of
    ours they use are ``FarmerVisitProduct`` rows, and having none is what
    "doesn't use our products" means (:attr:`uses_our_products`).

    ``village`` is stored resolved -- ``FieldTripOperations.create_farmer_visit``
    copies the trip's village when none is given.

    Exposed to the frontend by its ``public_id`` (``FV-…``).
    """

    public_id_prefix = "FV-"

    field_trip = models.ForeignKey(
        "aggregator.FieldTrip",
        verbose_name="field trip",
        on_delete=models.PROTECT,
        related_name="farmer_visits",
    )
    farmer_name = models.CharField("farmer name", max_length=255)
    contact_number = models.CharField(
        "contact number",
        max_length=10,
        validators=[validate_phone_number],
        help_text="10-digit mobile number, no country code.",
    )
    village = models.CharField("village", max_length=255)
    land_area_bigha = models.DecimalField(
        "land area in bigha",
        max_digits=12,
        decimal_places=4,
    )

    class Meta:
        verbose_name = "farmer visit"
        verbose_name_plural = "farmer visits"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["field_trip", "contact_number"],
                name="uniq_farmervisit_trip_contact",
            ),
            models.CheckConstraint(
                condition=models.Q(land_area_bigha__gte=0),
                name="ck_farmervisit_land_area_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.public_id}: {self.farmer_name}" if self.public_id else self.farmer_name

    @property
    def uses_our_products(self) -> bool:
        # ``.all()`` rather than ``.exists()`` so a prefetched list is reused.
        return bool(self.visit_products.all())
