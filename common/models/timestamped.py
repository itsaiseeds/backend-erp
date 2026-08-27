from django.db import models
from django.utils import timezone


def indian_now():
    """Return the current time in the project's timezone (Asia/Kolkata)."""
    return timezone.localtime(timezone.now())


class TimeStampedModel(models.Model):
    """Adds ``created_at`` and ``updated_at`` columns to a model."""

    created_at = models.DateTimeField(
        "created at", default=indian_now, editable=False
    )
    updated_at = models.DateTimeField("updated at", auto_now=True, editable=False)

    class Meta:
        abstract = True
