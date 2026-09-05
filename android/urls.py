"""Top-level Android app routing: ``/android/...``"""

from django.urls import include, path

urlpatterns = [
    path("api/", include("android.api.urls")),
]
