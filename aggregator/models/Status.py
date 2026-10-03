from __future__ import annotations

from enum import IntEnum

from django.db import models

from common.models import CreatedByModel, SoftDeletedModel, TimeStampedModel


class StatusIds(IntEnum):
    """``aggregator_status`` row ids — the single source of truth for CODE→id.

    Each member's ``name`` is exactly the seeded ``code`` and its ``value`` is
    the row ``id`` (see ``sql/dml.sql``): ids 1-7 are the order lifecycle, ids
    8-9 the client verification states, ids 10-11 the inward raw-material lot
    lifecycle, ids 12-15 the field-trip lifecycle, id 16 the inward
    raw-material lot's ``Rejected`` status (not contiguous with 10-11: it was
    added after the field-trip range was already seeded, and its ``code`` must
    differ from the unrelated order-lifecycle ``REJECTED`` at id 7), and ids
    17-19 the return-order lifecycle. No migrations — keep in sync with the
    seed rows.
    """

    BOOKED = 1
    UNDER_REVIEW = 2
    CONFIRMED = 3
    DISPATCHED = 4
    DELIVERED = 5
    ON_HOLD = 6
    REJECTED = 7
    VERIFICATION_PENDING = 8
    VERIFIED = 9
    LAB_TESTING = 10
    IN_USE = 11
    PLANNED = 12
    APPROVED = 13
    IN_PROGRESS = 14
    COMPLETED = 15
    RAW_MATERIAL_REJECTED = 16
    RETURN_PENDING = 17
    RETURN_ACCEPTED = 18
    RETURN_REJECTED = 19

    @classmethod
    def order_statuses(cls) -> list[StatusIds]:
        """The order lifecycle ids (1–7)."""
        return [cls(value) for value in range(cls.BOOKED, cls.REJECTED + 1)]

    @classmethod
    def client_statuses(cls) -> list[StatusIds]:
        """The client verification ids (8–9)."""
        return [cls(value) for value in range(cls.VERIFICATION_PENDING, cls.VERIFIED + 1)]

    @classmethod
    def raw_material_statuses(cls) -> list[StatusIds]:
        """The inward raw-material lot lifecycle ids (10–11, plus 16)."""
        return [cls.LAB_TESTING, cls.IN_USE, cls.RAW_MATERIAL_REJECTED]

    @classmethod
    def return_statuses(cls) -> list[StatusIds]:
        """The return-order lifecycle ids (17–19)."""
        return [cls.RETURN_PENDING, cls.RETURN_ACCEPTED, cls.RETURN_REJECTED]

    @classmethod
    def field_trip_statuses(cls) -> list[StatusIds]:
        """The field-trip lifecycle ids (12–15)."""
        return [cls(value) for value in range(cls.PLANNED, cls.COMPLETED + 1)]


class Status(TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A generic, enum-like status value shared across domains.

    Rows are seeded (see ``sql/dml.sql``) and referenced by ``Order``,
    ``Client``, ``InwardRawMaterial``, ``ReturnOrder`` and ``FieldTrip``. The table carries no
    transition rules; each consumer restricts which ``code`` values it
    accepts in its own ``clean()``.
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

    @classmethod
    def by_id(cls, status_id: StatusIds) -> Status:
        """Resolve a ``StatusIds`` member to its seeded ``aggregator_status`` row."""
        return cls.objects.get(id=status_id)

    def __str__(self):
        return self.name or self.code
