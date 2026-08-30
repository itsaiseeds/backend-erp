"""Routes for the ``/api/utilities/`` namespace (shared look-ups/helpers)."""

from django.urls import path

from .CitiesByStateView import CitiesByStateView

urlpatterns = [
    path("cities", CitiesByStateView.as_view(), name="cities-by-state"),
]
