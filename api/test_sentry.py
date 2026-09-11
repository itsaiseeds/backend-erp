"""Sentry error-tracking probe endpoint.

``GET/POST /api/test-sentry/`` raises an unhandled exception on purpose so you
can confirm error tracking is wired up (inspect it under Issues in
GlitchTip/Sentry, under the environment set by ``SENTRY_ENV``). Sentry only
initializes when ``SENTRY_DSN`` is set and ``DEBUG`` is false, so in
development this simply returns a Django error page.
"""

from __future__ import annotations

from .admin import AdminApiView


class TestSentryView(AdminApiView):
    """Force a 500 so its traceback is captured by error tracking.

    Only a Django superuser may call it, to stop the endpoint from being
    exploited as a free exception spammer.
    """

    superuser_required = True

    def get(self, request):
        raise ValueError("Sentry test exception from /api/test-sentry/")

    def post(self, request):
        raise ValueError("Sentry test exception from /api/test-sentry/")
