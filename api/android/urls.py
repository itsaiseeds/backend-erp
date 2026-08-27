"""Android app versioned routes: ``/api/android/...``"""

from django.urls import include, path

urlpatterns = [
    path("v1/", include("api.android.v1.urls")),
]
