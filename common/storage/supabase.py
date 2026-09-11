"""Supabase Storage backend — the deployed-environment image store.

A product picture is pushed to a **public** Supabase Storage bucket and only the
resulting URL is stored on the row (``Product.image_url``); Render's filesystem
is ephemeral, so nothing is kept locally.

Supabase's own client library is Node-only, so we call the Storage REST API
directly with ``requests`` (already a dependency). Configuration lives in
``config.settings``: ``SUPABASE_URL``, ``SUPABASE_SECRET_KEY`` and
``SUPABASE_STORAGE_BUCKET``. When they are unset this backend is simply not
selected — see ``common.storage.images`` for the dispatch.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

logger = logging.getLogger(__name__)

# Supabase is a third-party hop on the request path; fail fast rather than
# holding a gunicorn worker open.
_TIMEOUT_SECONDS = 15

_PUBLIC_URL_MARKER = "/storage/v1/object/public/"


def is_configured() -> bool:
    """Whether this environment has credentials for a Supabase bucket."""
    return bool(
        settings.SUPABASE_URL
        and settings.SUPABASE_SECRET_KEY
        and settings.SUPABASE_STORAGE_BUCKET
    )


def _public_prefix() -> str:
    return (
        f"{settings.SUPABASE_URL}{_PUBLIC_URL_MARKER}"
        f"{settings.SUPABASE_STORAGE_BUCKET}/"
    )


def _object_url(name: str) -> str:
    return (
        f"{settings.SUPABASE_URL}/storage/v1/object/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{name}"
    )


def put(image: UploadedFile, *, name: str, content_type: str) -> str:
    """Upload ``image`` to the bucket and return its public URL."""
    image.seek(0)
    response = requests.post(
        _object_url(name),
        data=image.read(),
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        timeout=_TIMEOUT_SECONDS,
    )
    if not response.ok:
        logger.error(
            "Supabase upload failed (%s): %s", response.status_code, response.text
        )
        raise serializers.ValidationError(
            "Could not upload the image. Please try again."
        )

    return f"{_public_prefix()}{name}"


def owns(url: str) -> bool:
    """Whether ``url`` points at an object in this environment's bucket."""
    return bool(url) and is_configured() and url.startswith(_public_prefix())


def remove(url: str) -> None:
    """Delete the object behind ``url``; log and continue if it cannot be removed."""
    name = url[len(_public_prefix()):]
    try:
        response = requests.delete(
            _object_url(name),
            headers={"Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}"},
            timeout=_TIMEOUT_SECONDS,
        )
        if not response.ok:
            logger.warning(
                "Supabase delete failed (%s) for %s: %s",
                response.status_code,
                name,
                response.text,
            )
    except requests.RequestException:
        logger.warning("Supabase delete errored for %s", name, exc_info=True)
