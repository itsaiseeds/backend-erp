"""Version-inheritance routing for the Android API.

Each ``vN`` package exposes a ``ROUTES: dict[str, type[APIView]]`` mapping a
URL sub-path to the view class introduced or changed at that version. A view
defined at ``vX`` is automatically served by every later ``vY`` where
``Y >= X`` unless some version in between overrides that same route -- this
module makes that guarantee structural instead of a convention someone has to
remember to uphold by hand when wiring urls.
"""

from __future__ import annotations

import importlib

from django.urls import path


def merged_routes(versions: list[str]) -> dict[str, type]:
    """Merge ``ROUTES`` from each version module in order; later versions win."""
    merged: dict[str, type] = {}
    for version in versions:
        module = importlib.import_module(f"android.api.{version}.routes")
        merged.update(module.ROUTES)
    return merged


def build_urlpatterns(versions: list[str]) -> list:
    """Build the urlpatterns for the last entry in ``versions``.

    ``versions`` is the ordered prefix of releases up to and including the one
    being built (e.g. ``["v1", "v2"]`` when building ``v2``), so every route
    ever introduced at or before this version is included, with a later
    version's own ``ROUTES`` entry taking priority over an earlier one for the
    same path.

    URL names are derived from the *route path* (not the view class) so two
    different routes that happen to share a view class -- e.g. an alias and a
    canonical path pointing at the same class -- never collide into one
    ``reverse()`` target.
    """
    merged = merged_routes(versions)
    current = versions[-1]
    return [
        path(route, view.as_view(), name=f"{current}-{route.replace('/', '-')}")
        for route, view in merged.items()
    ]
