import secrets
import string

from django.db import models

PUBLIC_ID_ALPHABET = string.ascii_uppercase + string.digits
PUBLIC_ID_LENGTH = 12

# Upper bound for a prefixed public id column: a short prefix ("PP-") plus the
# 12-char random body, with headroom.
PREFIXED_PUBLIC_ID_MAX_LENGTH = 20


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


class PrefixedPublicIdModel(models.Model):
    """A ``public_id`` of the form ``<prefix><12 random chars>`` (e.g. ``ORD-…``).

    Subclasses set ``public_id_prefix``. The id is generated on first save and
    is the only identifier exposed to the frontend; the primary key stays
    internal.
    """

    public_id_prefix = ""

    public_id = models.CharField(
        "public id",
        max_length=PREFIXED_PUBLIC_ID_MAX_LENGTH,
        editable=False,
        unique=True,
        db_index=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def _generate_public_id(self):
        return f"{self.public_id_prefix}{generate_public_id()}"

    def save(self, *args, **kwargs):
        if not self.public_id:
            for _ in range(5):
                candidate = self._generate_public_id()
                if not type(self).all_objects.filter(public_id=candidate).exists():
                    self.public_id = candidate
                    break
            else:
                self.public_id = self._generate_public_id()
        super().save(*args, **kwargs)
