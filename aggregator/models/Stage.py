from __future__ import annotations

from enum import IntEnum

from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class StageIds(IntEnum):
    """``aggregator_stage`` row ids — the single source of truth for CODE→id.

    Each member's ``name`` is exactly the seeded ``code`` and its ``value`` is
    the row ``id`` (see ``sql/dml.sql``). The four members are the whole set of
    seed classifications a ``Product`` can carry. No migrations — keep in sync
    with the seed rows.
    """

    BREEDER = 1
    FOUNDATION = 2
    RESEARCH = 3
    CERTIFICATE = 4


class Stage(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """The seed classification of a product (breeder, foundation, …).

    Rows are seeded (see ``sql/dml.sql``) and referenced by ``Product``. Like
    ``Status``, the table carries no transition rules — it is a fixed, enum-like
    vocabulary mirrored by ``StageIds``.
    """

    code = models.CharField("code", max_length=32, unique=True, db_index=True)
    name = models.CharField("name", max_length=64)
    sequence = models.PositiveSmallIntegerField(
        "sequence",
        default=0,
        help_text="Display ordering.",
    )

    class Meta:
        verbose_name = "stage"
        verbose_name_plural = "stages"
        ordering = ["sequence", "code"]

    @classmethod
    def by_id(cls, stage_id: StageIds) -> Stage:
        """Resolve a ``StageIds`` member to its seeded ``aggregator_stage`` row."""
        return cls.objects.get(id=stage_id)

    def __str__(self):
        return self.name or self.code
