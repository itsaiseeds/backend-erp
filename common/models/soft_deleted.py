from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models

from .timestamped import indian_now


class SoftDeletedManager(models.Manager):
    """Default manager that hides soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Manager that returns every record, including soft-deleted ones."""

    def get_queryset(self):
        return super().get_queryset()


class SoftDeletedModel(models.Model):
    """Adds soft-delete behaviour to a model.

    Records are not physically removed on ``delete()``; they are flagged with
    ``is_deleted``/``deleted_at`` and excluded from the default ``objects``
    manager.

    ``delete()`` takes an optional ``deleted_by`` user. The user is recorded in
    ``deleted_by`` and must hold the ``<app>.delete_<model>`` permission for
    this table, otherwise ``PermissionDenied`` is raised.
    """

    is_deleted = models.BooleanField(
        "deleted", default=False, editable=False, db_index=True
    )
    deleted_at = models.DateTimeField(
        "deleted at", null=True, blank=True, editable=False
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="deleted by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )

    # ``objects`` hides soft-deleted rows; ``all_objects`` shows everything.
    objects = SoftDeletedManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def _delete_permission_codename(self):
        return "{}.delete_{}".format(self._meta.app_label, self._meta.model_name)

    def delete(self, deleted_by=None, using=None, keep_parents=False):
        """Soft delete: flag the row instead of removing it.

        ``deleted_by`` must be provided and must hold the delete permission for
        this table.
        """
        if self.is_deleted:
            return

        if deleted_by is None:
            raise PermissionDenied(
                "A user must be provided to soft delete this record "
                "(deleted_by is required)."
            )

        if not deleted_by.has_perm(self._delete_permission_codename()):
            raise PermissionDenied(
                "User '{}' does not have permission to delete '{}'.".format(
                    deleted_by, self._meta.model_name
                )
            )

        self.deleted_by = deleted_by
        self.deleted_at = indian_now()
        self.is_deleted = True
        self.save(
            using=using,
            update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"],
        )

    def hard_delete(self, using=None, keep_parents=False):
        """Physically remove the row, bypassing soft-delete checks."""
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self, using=None):
        """Clear the deleted flags, bringing the record back."""
        if self.is_deleted:
            self.deleted_by = None
            self.deleted_at = None
            self.is_deleted = False
            self.save(
                using=using,
                update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"],
            )
