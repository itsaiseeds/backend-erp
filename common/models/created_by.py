from django.conf import settings
from django.db import models


class CreatedByModel(models.Model):
    """Adds a ``created_by`` user audit column to a model.

    The creator is protected: a user who created records cannot be deleted
    while those records reference them (``PROTECT`` == RESTRICT in Postgres).
    Admin sites never show the field: it is filled automatically with
    ``request.user`` on creation (see ``AuditFieldsAdminMixin.save_model``).
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="created by",
        on_delete=models.PROTECT,
        null=True,
        blank=False,
        related_name="+",
        help_text="User who created this record.",
    )

    class Meta:
        abstract = True
