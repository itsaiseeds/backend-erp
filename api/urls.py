"""Top-level API routing.

Every HTTP endpoint here is session-only and lives under ``/api/`` for the
sales admin website:

* ``/api/sales_admin/...``   - the sales admin website.
* ``/api/utilities/...``     - session-authenticated web helpers/look-ups.

The sales-person Android app is a separate Django app, served at
``/android/api/<version>/...`` (see ``android.urls``) and is token-only.
"""

from django.urls import include, path

urlpatterns = [
    path("sales_admin/", include("api.sales_admin.urls")),
    path("utilities/", include("api.utilities.urls")),
]
