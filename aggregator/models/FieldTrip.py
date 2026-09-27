from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import (
    CreatedByModel,
    PrefixedPublicIdModel,
    SoftDeletedModel,
    TimeStampedModel,
)

from .Status import StatusIds

FIELD_TRIP_STATUS_CODES = {s.name for s in StatusIds.field_trip_statuses()}
APPROVAL_REQUIRED_STATUS_CODES = {
    StatusIds.APPROVED.name,
    StatusIds.IN_PROGRESS.name,
    StatusIds.COMPLETED.name,
}
START_REQUIRED_STATUS_CODES = {StatusIds.IN_PROGRESS.name, StatusIds.COMPLETED.name}
DELETABLE_STATUS_CODES = frozenset({StatusIds.PLANNED.name, StatusIds.APPROVED.name})


class FieldTrip(PrefixedPublicIdModel, TimeStampedModel, SoftDeletedModel, CreatedByModel):
    """A sales person's visit to a village, where they meet farmers.

    Planned by a sales person (``created_by``) and approved by a sales admin
    (``approved_by`` / ``approved_at``) before it may start. The lifecycle is
    PLANNED -> APPROVED -> IN_PROGRESS -> COMPLETED; ``started_at`` /
    ``ended_at`` are the server times it actually started and ended, beside the
    planned ``expected_*`` window.

    A trip that has started is history: it can no longer be deleted (see
    :meth:`delete` / :meth:`mark_deleted`). Farmers met on the trip are
    ``FarmerVisit`` rows.

    Exposed to the frontend by its ``public_id`` (``FT-…``).
    """

    public_id_prefix = "FT-"

    city = models.ForeignKey(
        "aggregator.City",
        verbose_name="city",
        on_delete=models.PROTECT,
        related_name="field_trips",
    )
    village = models.CharField("village", max_length=255)
    status = models.ForeignKey(
        "aggregator.Status",
        verbose_name="status",
        on_delete=models.PROTECT,
        related_name="field_trips",
    )
    expected_start_at = models.DateTimeField("expected start at")
    expected_end_at = models.DateTimeField("expected end at")
    started_at = models.DateTimeField("started at", null=True, blank=True)
    ended_at = models.DateTimeField("ended at", null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="approved by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Sales admin who approved this field trip.",
    )
    approved_at = models.DateTimeField("approved at", null=True, blank=True)

    class Meta:
        verbose_name = "field trip"
        verbose_name_plural = "field trips"
        ordering = ["-expected_start_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expected_end_at__gt=models.F("expected_start_at")),
                name="ck_fieldtrip_expected_window",
            ),
            models.CheckConstraint(
                condition=models.Q(ended_at__isnull=True)
                | models.Q(ended_at__gte=models.F("started_at")),
                name="ck_fieldtrip_actual_window",
            ),
            models.UniqueConstraint(
                fields=["created_by"],
                condition=models.Q(status_id=StatusIds.IN_PROGRESS, is_deleted=False),
                name="uniq_fieldtrip_one_in_progress_per_sales_person",
            ),
        ]

    def __str__(self):
        return self.public_id or "Field trip"

    @property
    def status_code(self) -> str | None:
        return self.status.code if self.status_id else None

    def clean(self):
        super().clean()
        errors = {}
        code = self.status_code

        if code is not None and code not in FIELD_TRIP_STATUS_CODES:
            errors["status"] = "Invalid status for a field trip."

        if code in APPROVAL_REQUIRED_STATUS_CODES and (
            self.approved_by_id is None or self.approved_at is None
        ):
            errors["status"] = "An approved field trip must record who approved it and when."

        if code in START_REQUIRED_STATUS_CODES and self.started_at is None:
            errors["started_at"] = "A started field trip must record when it started."

        if code == StatusIds.COMPLETED.name and self.ended_at is None:
            errors["ended_at"] = "A completed field trip must record when it ended."

        if (
            self.expected_start_at
            and self.expected_end_at
            and self.expected_end_at <= self.expected_start_at
        ):
            errors["expected_end_at"] = "The expected end must be after the expected start."

        if self.approved_by_id and not (
            self.approved_by.is_admin_user or self.approved_by.is_superuser
        ):
            errors["approved_by"] = "Field trips can only be approved by a sales admin."

        if self.created_by_id and not self.created_by.is_salesperson:
            errors["created_by"] = "Field trips can only be created by a sales person."

        if errors:
            raise ValidationError(errors)

    def _assert_deletable(self):
        if self.status_code not in DELETABLE_STATUS_CODES:
            raise ValidationError(
                {
                    "status": (
                        f"Cannot delete a field trip that is {self.status_code}. "
                        f"Allowed: {', '.join(sorted(DELETABLE_STATUS_CODES))}."
                    )
                }
            )

    def delete(self, deleted_by=None, using=None, keep_parents=False):
        self._assert_deletable()
        return super().delete(deleted_by=deleted_by, using=using, keep_parents=keep_parents)

    def mark_deleted(self, actor, using=None):
        self._assert_deletable()
        return super().mark_deleted(actor, using=using)
