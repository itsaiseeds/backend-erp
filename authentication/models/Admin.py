from django.core.exceptions import ValidationError
from django.db import models

from common.models import SoftDeletedModel, TimeStampedModel


class Admin(TimeStampedModel, SoftDeletedModel):
    """Application admin. Only a superuser can create one."""

    user = models.OneToOneField(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="admin_profile",
    )

    class Meta:
        verbose_name = "admin"
        verbose_name_plural = "admins"

    def __str__(self):
        return f"Admin: {self.user}"

    def clean(self):
        super().clean()
        if self.user_id is None:
            return
        creator = self.user.created_by
        if creator is None:
            # Superusers are created by nobody -> they are the only ones allowed.
            if not self.user.is_superuser:
                raise ValidationError(
                    "An Admin must be created by a superuser (created_by required)."
                )
        elif not creator.is_superuser:
            raise ValidationError(
                {"user": {"created_by": "Only a superuser can create an Admin."}}
            )
