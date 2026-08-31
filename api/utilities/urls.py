"""Routes for the ``/api/utilities/`` namespace (shared look-ups/helpers).

Every endpoint here is restricted to a Django superuser (enforced per-view).
"""

from django.urls import path

from .CitiesView import CitiesView

urlpatterns = [
    path("cities", CitiesView.as_view(), name="cities"),
]
