"""Development-only middleware.

Nothing here may run with ``DEBUG=False``; each class asserts that itself so a
misconfigured production deployment fails loudly instead of silently relaxing a
security control.
"""

from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings

_LOCAL_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "[::1]", "::1"})


def _is_local_origin(origin: str) -> bool:
    """True when ``origin`` is an http:// URL pointing at this machine."""
    if not origin:
        return False

    parsed = urlparse(origin)
    if parsed.scheme != "http":
        return False

    return (parsed.hostname or "") in _LOCAL_HOSTNAMES


class TrustLocalhostCsrfOriginMiddleware:
    """Trust any localhost origin for CSRF while developing.

    ``flutter run -d chrome`` picks a random high port unless ``--web-port`` is
    passed, and ``CSRF_TRUSTED_ORIGINS`` cannot wildcard ports -- Django's
    wildcard syntax covers subdomains only. Rather than enumerate 64k origins,
    this appends just the origin of the request actually being handled, and only
    when it is a loopback http:// origin.

    Must be placed *before* ``CsrfViewMiddleware`` so the value is in place when
    the CSRF check runs.
    """

    def __init__(self, get_response):
        if not settings.DEBUG:
            raise RuntimeError(
                "TrustLocalhostCsrfOriginMiddleware must never run with "
                "DEBUG=False; remove it from MIDDLEWARE in production."
            )
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get("HTTP_ORIGIN", "")

        if _is_local_origin(origin) and origin not in settings.CSRF_TRUSTED_ORIGINS:
            settings.CSRF_TRUSTED_ORIGINS.append(origin)

        return self.get_response(request)
