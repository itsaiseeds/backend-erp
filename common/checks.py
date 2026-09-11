"""Deploy-time sanity checks for the shared infrastructure in ``common``.

Registered from ``CommonConfig.ready()`` and therefore run by
``manage.py check`` (and by every other management command, including the
``collectstatic`` the container entrypoint runs on boot).
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Warning as CheckWarning


def supabase_configured_when_deployed(app_configs, **kwargs) -> list[CheckWarning]:
    """Warn when a non-DEBUG environment would store images on local disk.

    The fallback to ``MEDIA_ROOT`` is what makes uploads work in development and
    in tests, but on Render the filesystem is ephemeral: images written there
    disappear on the next deploy. Missing credentials should be noisy, not a
    silent data-loss bug.
    """
    from common.storage import supabase

    if supabase.is_configured():
        return []
    return [
        CheckWarning(
            "Product images will be stored on local disk, which is ephemeral.",
            hint=(
                "Set SUPABASE_URL, SUPABASE_SECRET_KEY and "
                "SUPABASE_STORAGE_BUCKET so uploads go to the Supabase bucket."
            ),
            id="common.W001",
        )
    ]
