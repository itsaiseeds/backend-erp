"""Deploy-time sanity checks for the shared infrastructure in ``common``.

Registered from ``CommonConfig.ready()`` and therefore run by
``manage.py check`` (and by every other management command, including the
``collectstatic`` the container entrypoint runs on boot).
"""

from __future__ import annotations

from django.core.checks import Warning as CheckWarning


def images_have_durable_storage(app_configs, **kwargs) -> list[CheckWarning]:
    """Warn whenever uploads would land on local disk instead of a bucket.

    The fallback to ``MEDIA_ROOT`` is what makes uploads work in development and
    in tests, so this fires there too -- deliberately. ``DEBUG`` is not a usable
    proxy for "deployed": preprod runs with ``DEBUG=True`` and a real bucket. The
    only question worth asking is whether the files will outlive the container,
    and on Render they will not: anything written to local disk disappears on
    the next deploy. Missing credentials should be noisy, not a silent
    data-loss bug.
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
