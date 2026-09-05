"""Unit tests for the Android API's version-inheritance routing mechanism.

``android.api.routing`` guarantees that a view introduced at ``vX`` is served
by every later ``vY`` (``Y >= X``) unless a version in between overrides that
route -- these tests cover the real ``v1`` wiring and, via a synthetic ``v2``
routes module, the actual inherit-then-override behavior for a future version.
"""

from __future__ import annotations

import sys
import types

from django.urls import resolve
from django.urls.exceptions import Resolver404

from android.api import routing
from android.api.v1 import routes as v1_routes
from android.api.v1.CitiesView import CitiesView
from android.api.v1.LoginView import LoginView
from android.api.v1.LogoutView import LogoutView
from android.api.v1.ReauthenticateView import ReauthenticateView


def test_v1_routes_resolve_under_the_v1_url_prefix():
    """tests/android/test_routing.py::test_v1_routes_resolve_under_the_v1_url_prefix"""
    cases = {
        "/android/api/v1/auth/login": LoginView,
        "/android/api/v1/auth/logout": LogoutView,
        "/android/api/v1/auth/reauthenticate": ReauthenticateView,
        "/android/api/v1/utilities/cities": CitiesView,
    }
    for path, view_class in cases.items():
        match = resolve(path)
        assert match.func.view_class is view_class, path


def test_merged_routes_for_v1_alone_returns_v1_routes():
    """tests/android/test_routing.py::test_merged_routes_for_v1_alone_returns_v1_routes"""
    assert routing.merged_routes(["v1"]) == v1_routes.ROUTES


def test_a_later_version_inherits_earlier_routes_it_does_not_override(monkeypatch):
    """A synthetic v2 that only adds one new route still serves every v1 route.

    tests/android/test_routing.py::test_a_later_version_inherits_earlier_routes_it_does_not_override
    """
    fake_v2_routes = types.ModuleType("android.api.v2.routes")
    fake_v2_routes.ROUTES = {"ping": LoginView}  # arbitrary new route at v2
    monkeypatch.setitem(sys.modules, "android.api.v2.routes", fake_v2_routes)

    merged = routing.merged_routes(["v1", "v2"])

    # Every v1 route is still present (y >= x backwards compatibility)...
    for route, view_class in v1_routes.ROUTES.items():
        assert merged[route] is view_class
    # ...and the new v2-only route is present too.
    assert merged["ping"] is LoginView


def test_a_later_version_overrides_a_shared_route(monkeypatch):
    """A v2 route sharing a v1 key wins over the v1 view for that path.

    tests/android/test_routing.py::test_a_later_version_overrides_a_shared_route
    """
    fake_v2_routes = types.ModuleType("android.api.v2.routes")
    fake_v2_routes.ROUTES = {
        "utilities/cities": LoginView
    }  # deliberately overrides v1's CitiesView
    monkeypatch.setitem(sys.modules, "android.api.v2.routes", fake_v2_routes)

    merged = routing.merged_routes(["v1", "v2"])

    assert merged["utilities/cities"] is LoginView
    # Untouched v1 routes are unaffected by the override.
    assert merged["auth/login"] is v1_routes.ROUTES["auth/login"]


def test_a_v2_only_route_is_unreachable_under_v1():
    """A route first introduced at v2 must not resolve under /android/api/v1/.

    tests/android/test_routing.py::test_a_v2_only_route_is_unreachable_under_v1
    """
    try:
        resolve("/android/api/v1/ping")
    except Resolver404:
        pass
    else:
        raise AssertionError("a v2-only route must not resolve under v1")
