from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class Status(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A generic, enum-like status value shared across domains.

    Rows are seeded (see ``sql/dml.sql``) and referenced by ``Order`` and
    ``Client``. The table carries no transition rules; each consumer restricts
    which ``code`` values it accepts in its own ``clean()``.
    """

    code = models.CharField("code", max_length=32, unique=True, db_index=True)
    name = models.CharField("name", max_length=64)
    sequence = models.PositiveSmallIntegerField(
        "sequence",
        default=0,
        help_text="Display ordering within a domain.",
    )

    class Meta:
        verbose_name = "status"
        verbose_name_plural = "statuses"
        ordering = ["sequence", "code"]

    def __str__(self):
        return self.name or self.code
