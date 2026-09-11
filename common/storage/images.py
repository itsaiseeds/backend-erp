"""Product image uploads, over whichever storage backend this environment has.

One entry point, two backends, chosen by configuration:

* **Supabase Storage** (``common.storage.supabase``) whenever ``SUPABASE_URL``
  and ``SUPABASE_SECRET_KEY`` are set — i.e. deployed environments, where the
  local filesystem is ephemeral and files have to outlive the container.
* **The local disk** (``common.storage.local``), under ``MEDIA_ROOT``, when they
  are not — development and tests. Uploads work exactly the same way there; the
  files simply land in ``media/`` and are served by the dev server.

``delete_image`` keys off the *shape of the stored URL* rather than the current
backend, so images written to disk before a Supabase bucket existed still get
cleaned up afterwards.
"""

from __future__ import annotations

import uuid

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from . import local, supabase

# Content types we accept, mapped to the extension we store the file under.
ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_image(image: UploadedFile) -> tuple[str, str]:
    """Check type and size, returning ``(content_type, extension)``.

    Backend-independent: the same limits apply on disk and in the bucket, so a
    picture that is accepted in development is accepted in production too.
    """
    content_type = (image.content_type or "").split(";")[0].strip().lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise serializers.ValidationError(
            "Image must be a JPEG, PNG or WebP file."
        )
    if image.size is None or image.size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError(
            f"Image must be {MAX_IMAGE_BYTES // (1024 * 1024)} MB or smaller."
        )
    return content_type, extension


def upload_image(image: UploadedFile, *, folder: str) -> str:
    """Store ``image`` and return the URL to save on the row.

    The file is named by a fresh UUID rather than by any model field, so the
    upload can happen *before* the row exists — a failed upload therefore never
    leaves a half-created product behind.

    Returns an absolute ``https://…`` URL on Supabase, or a ``MEDIA_URL``-relative
    path (``/media/products/….png``) on disk.
    """
    content_type, extension = validate_image(image)
    name = f"{folder}/{uuid.uuid4().hex}.{extension}"

    if supabase.is_configured():
        return supabase.put(image, name=name, content_type=content_type)
    return local.put(image, name=name)


def delete_image(url: str) -> None:
    """Best-effort delete of a previously stored image.

    Used when an image is replaced, so old files do not pile up. Failures are
    logged and swallowed by the backends: an orphaned file is cheap, and it must
    never turn a successful update into an error for the caller. A URL neither
    backend recognises (hand-set, another bucket, an old project) is left alone.
    """
    if not url:
        return
    if supabase.owns(url):
        supabase.remove(url)
    elif local.owns(url):
        local.remove(url)
