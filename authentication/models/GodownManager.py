from collections.abc import Callable

from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel

from ..credentials import revoke_user_credentials


class GodownManager(CreatedByModel, TimeStampedModel, SoftDeletedModel):
    """Godown (warehouse) manager. Only an application Admin (or superuser) may
    grant this role (enforced in the admin site via
    ``GodownManagerAdmin.has_add_permission``); the acting user is recorded in
    ``created_by``.

    Carries no location: nothing in the inward domain is scoped by one."""

    user = models.OneToOneField(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="godown_manager_profile",
    )

    class Meta:
        verbose_name = "godown manager"
        verbose_name_plural = "godown managers"

    def guard_soft_delete(self, perform: Callable[[], None]) -> None:
        """Losing the godown manager role logs the user out of every session and token."""
        perform()
        revoke_user_credentials(self.user)

    def __str__(self):
        return f"GodownManager: {self.user}"
