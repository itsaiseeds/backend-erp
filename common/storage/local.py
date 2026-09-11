"""On-disk image storage under ``MEDIA_ROOT`` — the development/test backend.

Used whenever Supabase is not configured (see ``common.storage.images``). Files
land in ``media/`` (gitignored) and the dev server serves them from ``MEDIA_URL``
(wired up in ``config/urls.py``, ``DEBUG`` only). Deployed environments never use
this backend: Render's filesystem is ephemeral, so anything written here would
vanish on the next deploy.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


def _storage() -> FileSystemStorage:
    """A storage instance built fresh, so ``override_settings`` is honoured."""
    return FileSystemStorage()


def put(image: UploadedFile, *, name: str) -> str:
    """Write ``image`` to disk and return its ``MEDIA_URL``-relative path."""
    storage = _storage()
    image.seek(0)
    # ``save`` may uniquify the name; use whatever it actually wrote.
    return storage.url(storage.save(name, image))


def owns(url: str) -> bool:
    """Whether ``url`` points at a file this backend wrote."""
    return bool(url) and url.startswith(settings.MEDIA_URL)


def remove(url: str) -> None:
    """Delete the file behind ``url``; log and continue if it cannot be removed."""
    name = url[len(settings.MEDIA_URL):]
    try:
        _storage().delete(name)
    except OSError:
        logger.warning("Could not delete media file %s", name, exc_info=True)
