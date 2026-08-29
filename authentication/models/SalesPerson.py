from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class SalesPerson(CreatedByModel, TimeStampedModel, SoftDeletedModel):
    """Sales person. Only an application Admin (or superuser) may grant this
    role (enforced in the admin site via ``SalesPersonAdmin.has_add_permission``);
    the acting user is recorded in ``created_by``."""

    user = models.OneToOneField(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="salesperson_profile",
    )

    city = models.ForeignKey(
        "aggregator.City",
        verbose_name="city",
        on_delete=models.PROTECT,
        related_name="sales_people",
    )

    class Meta:
        verbose_name = "sales person"
        verbose_name_plural = "sales people"

    def __str__(self):
        return f"SalesPerson: {self.user}"
