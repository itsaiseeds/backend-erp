"""Top-level API routing.

Every HTTP endpoint lives under ``/api/`` and is namespaced by client/app:

* ``/api/sales_admin/...``   - the sales admin website (mounted last).
* ``/api/android/<v>/...``   - the sales-person Android app, versioned.
"""

from django.urls import include, path

urlpatterns = [
    path("android/", include("api.android.urls")),
    path("sales_admin/", include("api.sales_admin.urls")),
    path("utilities/", include("api.utilities.urls")),
]
