"""Routes for the ``/api/utilities/`` namespace (shared look-ups/helpers).

Auth requirements are enforced per-view: ``cities`` is superuser-only,
``reauthenticate`` accepts any authenticated caller (session or bearer token).
"""

from django.urls import path

from .CitiesView import CitiesView
from .ReauthenticateView import ReauthenticateView

urlpatterns = [
    path("cities", CitiesView.as_view(), name="cities"),
    path("reauthenticate", ReauthenticateView.as_view(), name="reauthenticate"),
]
