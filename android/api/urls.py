"""Android API versioned routes: ``/android/api/<version>/...``

Version inheritance: a view introduced in ``vX`` is served under ``vY`` for
every ``Y >= X``, unless ``vY`` (or an intermediate version) overrides that
route in its own ``routes.ROUTES``. Add a new version by appending its name to
``VERSIONS`` below and giving it a ``routes.py`` that declares only the routes
it adds or changes -- everything else is inherited automatically.
"""

from __future__ import annotations

from django.urls import include, path

from .routing import build_urlpatterns

VERSIONS = ["v1"]

urlpatterns = [
    path(f"{version}/", include(build_urlpatterns(VERSIONS[: index + 1])))
    for index, version in enumerate(VERSIONS)
]
