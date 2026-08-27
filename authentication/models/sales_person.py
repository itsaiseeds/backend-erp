from django.core.exceptions import ValidationError
from django.db import models

from common.models import SoftDeletedModel, TimeStampedModel


class SalesPerson(TimeStampedModel, SoftDeletedModel):
    """Sales person. Only an application Admin (or superuser) can create one."""

    user = models.OneToOneField(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="salesperson_profile",
    )

    class Meta:
        verbose_name = "sales person"
        verbose_name_plural = "sales people"

    def __str__(self):
        return f"SalesPerson: {self.user}"

    def clean(self):
        super().clean()
        if self.user_id is None:
            return
        creator = self.user.created_by
        if creator is None:
            if not self.user.is_superuser:
                raise ValidationError(
                    "A SalesPerson must be created by an Admin (created_by required)."
                )
        elif not (creator.is_superuser or creator.is_admin_user):
            raise ValidationError(
                {
                    "user": {
                        "created_by": "Only an Admin (or superuser) can create a SalesPerson."
                    }
                }
            )
