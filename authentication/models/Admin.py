from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class Admin(CreatedByModel, TimeStampedModel, SoftDeletedModel):
    """Application admin. Only a superuser may grant this role (enforced in the
    admin site via ``AdminProfileAdmin.has_add_permission``); the acting user is
    recorded in ``created_by``."""

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
