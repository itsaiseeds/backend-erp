"""Reusable DRF permission classes, keyed off the custom user model.

Each concrete permission gates on a role helper already present on the
``authentication.User`` model (``is_admin_user``, ``is_superuser``, ...).
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsRolePermission(BasePermission):
    """Gate on a helper present on the user model.

    Subclasses set :attr:`role_property` to the name of a boolean attribute or
    method on the authenticated user, e.g. ``is_admin_user``.
    """

    role_property: str | None = None

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if self.role_property is None:
            return False
        return bool(getattr(user, self.role_property, False))


class IsAdminUser(IsRolePermission):
    """Allow only users holding an application ``Admin`` profile."""

    role_property = "is_admin_user"


class IsSuperUser(IsRolePermission):
    """Allow only Django superusers."""

    role_property = "is_superuser"


class IsSalesPerson(IsAuthenticated):
    """Allow only users holding a ``SalesPerson`` profile."""

    def has_permission(self, request, view) -> bool:
        if not super().has_permission(request, view):
            return False
        return request.user.is_salesperson
