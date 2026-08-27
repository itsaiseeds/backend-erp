import uuid

from django.db import models


class RandomIdModel(models.Model):
    """Adds a separate, indexed random UUID column (not the primary key)."""

    random_id = models.UUIDField(
        "random id",
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    class Meta:
        abstract = True
