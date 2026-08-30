"""Sentry error-tracking probe endpoint.

``POST/GET /api/test-sentry/`` raises an unhandled exception on purpose so you
can confirm error tracking is wired up in production (inspect it under Issues
in GlitchTip). Sentry only initializes when ``SENTRY_DSN`` is set and
``DEBUG`` is false, so in development this simply returns a Django error page.
"""

from __future__ import annotations

from .views import BaseApiView


class TestSentryView(BaseApiView):
    """Force a 500 so its traceback is captured by error tracking.

    Only a Django superuser may call it, to stop the public-facing endpoint
    from being exploited as a free exception spammer.
    """

    superuser_required = True

    def get(self, request):
        raise ValueError("Sentry test exception from /api/test-sentry/")

    def post(self, request):
        raise ValueError("Sentry test exception from /api/test-sentry/")
