"""Routes for the ``/api/utilities/`` namespace (session-only web helpers).

Auth requirements are enforced per-view: ``cities``, ``countries`` and
``states`` are superuser-only, ``reauthenticate`` accepts any authenticated
session. See ``android.api.v1.routes`` for the Android app's token-only
counterparts.
"""

from django.urls import path

from .CitiesView import CitiesView
from .CountriesView import CountriesView
from .ReauthenticateView import ReauthenticateView
from .StatesView import StatesView

urlpatterns = [
    path("cities", CitiesView.as_view(), name="cities"),
    path("countries", CountriesView.as_view(), name="countries"),
    path("reauthenticate", ReauthenticateView.as_view(), name="reauthenticate"),
    path("states", StatesView.as_view(), name="states"),
]
