from collections.abc import Callable

from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel

from ..credentials import revoke_user_credentials


class LabTester(CreatedByModel, TimeStampedModel, SoftDeletedModel):
    """Lab tester: the only role that may decide whether an inward raw-material
    lot passes or fails its lab test. Only an application Admin (or superuser)
    may grant this role (enforced in the admin site via
    ``LabTesterAdmin.has_add_permission``); the acting user is recorded in
    ``created_by``.

    Carries no location: nothing in the lab domain is scoped by one."""

    user = models.OneToOneField(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="lab_tester_profile",
    )

    class Meta:
        verbose_name = "lab tester"
        verbose_name_plural = "lab testers"

    def guard_soft_delete(self, perform: Callable[[], None]) -> None:
        """Losing the lab tester role logs the user out of every session and token."""
        perform()
        revoke_user_credentials(self.user)

    def __str__(self):
        return f"LabTester: {self.user}"
