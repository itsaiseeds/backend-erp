import secrets
import string

from django.db import models

PUBLIC_ID_ALPHABET = string.ascii_uppercase + string.digits
PUBLIC_ID_LENGTH = 12


def generate_public_id():
    """Random 12-char id from uppercase letters and digits."""
    return "".join(secrets.choice(PUBLIC_ID_ALPHABET) for _ in range(PUBLIC_ID_LENGTH))


class PublicIdModel(models.Model):
    """Adds a user-facing ``public_id`` reference id alongside the primary key.

    Use this on models whose id is shown to users (orders, invoices, etc.) so
    the internal primary key is never exposed.
    """

    public_id = models.CharField(
        "public id",
        max_length=PUBLIC_ID_LENGTH,
        default=generate_public_id,
        editable=False,
        unique=True,
        db_index=True,
    )

    class Meta:
        abstract = True
