"""Routes for the ``/api/utilities/`` namespace (session-only web helpers).

Auth requirements are enforced per-view: ``cities`` is superuser-only,
``reauthenticate`` accepts any authenticated session. See
``android.api.v1.routes`` for the Android app's token-only counterparts.
"""

from django.urls import path

from .CitiesView import CitiesView
from .ReauthenticateView import ReauthenticateView

urlpatterns = [
    path("cities", CitiesView.as_view(), name="cities"),
    path("reauthenticate", ReauthenticateView.as_view(), name="reauthenticate"),
]
