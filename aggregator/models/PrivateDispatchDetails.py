from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from authentication.validators import validate_phone_number
from common.models import SoftDeletedModel, TimeStampedModel


class PrivateDispatchDetails(TimeStampedModel, SoftDeletedModel):
    """Dispatch on our own vehicle (carries vehicle and driver details).

    Recorded by a sales admin (``dispatched_by``); it has no ``created_by``.
    """

    client = models.ForeignKey(
        "aggregator.Client",
        verbose_name="client",
        on_delete=models.PROTECT,
        related_name="private_dispatch_details",
    )
    dispatched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="dispatched by",
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Sales admin who recorded this dispatch.",
    )
    dispatch_date = models.DateField("dispatch date")
    from_city = models.ForeignKey(
        "aggregator.City",
        verbose_name="from city",
        on_delete=models.PROTECT,
        related_name="private_dispatches_from",
    )
    to_city = models.ForeignKey(
        "aggregator.City",
        verbose_name="to city",
        on_delete=models.PROTECT,
        related_name="private_dispatches_to",
    )
    vehicle_number = models.CharField("vehicle number", max_length=32)
    driver_number = models.CharField(
        "driver number",
        max_length=10,
        validators=[validate_phone_number],
    )

    class Meta:
        verbose_name = "private dispatch details"
        verbose_name_plural = "private dispatch details"
        ordering = ["-dispatch_date"]

    def __str__(self):
        return f"Vehicle {self.vehicle_number}"

    def clean(self):
        super().clean()
        errors = {}

        if self.dispatched_by_id and not (
            self.dispatched_by.is_admin_user or self.dispatched_by.is_superuser
        ):
            errors["dispatched_by"] = "Dispatch can only be recorded by a sales admin."

        if errors:
            raise ValidationError(errors)
