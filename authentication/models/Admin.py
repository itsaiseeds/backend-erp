from collections.abc import Callable

from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel

from ..credentials import revoke_user_credentials


class Admin(CreatedByModel, TimeStampedModel, SoftDeletedModel):
    """Application admin. Only a superuser may grant this role (enforced in the
    admin site via ``AdminProfileAdmin.has_add_permission``); the acting user is
    recorded in ``created_by``."""

    user = models.OneToOneField(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="admin_profile",
    )

    can_update_stock_count = models.BooleanField(default=False)
    share_contact = models.BooleanField(
        default=False,
        help_text="List this admin's name and phone number to the Android apps.",
    )

    class Meta:
        verbose_name = "admin"
        verbose_name_plural = "admins"

    def guard_soft_delete(self, perform: Callable[[], None]) -> None:
        """Losing the admin role logs the user out of every session and token."""
        perform()
        revoke_user_credentials(self.user)

    def __str__(self):
        return f"Admin: {self.user}"
