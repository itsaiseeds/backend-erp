"""Top-level API routing.

Every HTTP endpoint here is session-only and lives under ``/api/`` for the
sales admin website:

* ``/api/sales-admin/...``   - the sales admin website.
* ``/api/utilities/...``     - session-authenticated web helpers/look-ups.
* ``/api/test-sentry/``      - superuser-only probe that raises to test Sentry.
* ``/api/execute-code/``     - run Python on the server (``execute_python_code``
  permission only); its UI is the ``/execute-code/`` page.

The sales-person Android app is a separate Django app, served at
``/android/api/<version>/...`` (see ``android.urls``) and is token-only.
"""

from django.urls import include, path

from .execute_code import ExecuteCodeView
from .test_sentry import TestSentryView

urlpatterns = [
    path("sales-admin/", include("api.sales_admin.urls")),
    path("utilities/", include("api.utilities.urls")),
    path("test-sentry/", TestSentryView.as_view(), name="test-sentry"),
    path("execute-code/", ExecuteCodeView.as_view(), name="execute-code"),
]
