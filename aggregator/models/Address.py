from django.core.exceptions import ValidationError
from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class Address(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A physical address.

    Carries denormalised references to the entire geographic hierarchy
    (pincode, city, state, country) so that addresses can always be listed and
    filtered by any level. ``clean()`` keeps the chain consistent.
    """

    address_line_1 = models.CharField("address line 1", max_length=255)
    address_line_2 = models.CharField("address line 2", max_length=255, blank=True)
    pincode = models.ForeignKey(
        "aggregator.Pincode",
        verbose_name="pincode",
        on_delete=models.PROTECT,
        related_name="addresses",
    )
    city = models.ForeignKey(
        "aggregator.City",
        verbose_name="city",
        on_delete=models.PROTECT,
        related_name="addresses",
    )
    state = models.ForeignKey(
        "aggregator.State",
        verbose_name="state",
        on_delete=models.PROTECT,
        related_name="addresses",
    )
    country = models.ForeignKey(
        "aggregator.Country",
        verbose_name="country",
        on_delete=models.PROTECT,
        related_name="addresses",
    )

    class Meta:
        verbose_name = "address"
        verbose_name_plural = "addresses"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.address_line_1}, {self.city}" if self.city_id else self.address_line_1

    def clean(self):
        super().clean()
        errors = {}

        if self.pincode_id:
            pincode = self.pincode
            if pincode.city_id is None or pincode.city.state_id is None:
                errors["pincode"] = "Pincode is missing its city/state chain."
            else:
                if self.city_id != pincode.city_id:
                    errors["city"] = "City does not match the selected pincode."
                if self.state_id != pincode.city.state_id:
                    errors["state"] = "State does not match the selected pincode."
                if self.country_id != pincode.city.state.country_id:
                    errors["country"] = "Country does not match the selected pincode."
        else:
            errors["pincode"] = "Pincode is required."

        if self.city_id and self.state_id and self.city.state_id != self.state_id:
            errors["state"] = "State does not match the selected city."
        if self.state_id and self.country_id and self.state.country_id != self.country_id:
            errors["country"] = "Country does not match the selected state."

        if errors:
            raise ValidationError(errors)
