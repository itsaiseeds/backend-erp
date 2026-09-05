"""Flag-driven base views for the whole API.

A child view declares *what* it needs (authentication, role level) by setting
class flags, and the base view answers them — instead of every view re-checking
the same conditions by hand.

While the flags are the public interface the child sets, the implementation
delegates to Django REST Framework's ``authentication_classes`` /
``permission_classes`` (and therefore its serializers, parsers, throttling and
pagination all keep working).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .permissions import IsAdminUser, IsSalesPerson, IsSuperUser


def fire_and_forget(func: Callable[[], Any]) -> None:
    """Run ``func`` in a background thread after the current transaction commits.

    Use this for low-priority, "nice to have" work that must never fail the API
    response (audit logs, notifications, cache warming, ...). ``func`` runs
    exactly once the surrounding transaction has committed, in a daemon thread,
    and any exception it raises is swallowed and never propagated to the caller.
    """
    thread = threading.Thread(target=func, daemon=True, name="fire-and-forget")
    transaction.on_commit(thread.start)


class BaseApiView(APIView):
    """Base for every API view, configured by flags a child may set.

    Flags
    -----
    * ``auth_required``    - require an authenticated user (default ``True``).
    * ``admin_required``   - additionally require an ``Admin`` profile.
    * ``superuser_required`` - additionally require a Django superuser.
    * ``salesperson_required`` - additionally require a ``SalesPerson`` profile.

    The concrete client bases (:class:`~api.admin.AdminApiView` for the
    session-only web app and :class:`~android.api.base.AndroidBaseView` for
    the token-only Android app) fix which *credentials* authenticate a
    request; this class only combines the role flags into ready-made
    permission checks and does not itself pick an authentication scheme --
    every concrete view must go through one of those two bases.

    Because :meth:`get_permissions` is overridden here, a subclass's
    ``permission_classes`` attribute (the normal DRF hook) is never
    consulted -- express every role requirement as one of the flags above.
    """

    auth_required = True
    admin_required = False
    superuser_required = False
    salesperson_required = False

    def get_permissions(self):
        permissions = []
        if self.auth_required:
            permissions.append(IsAuthenticated())
        if self.admin_required:
            permissions.append(IsAdminUser())
        if self.superuser_required:
            permissions.append(IsSuperUser())
        if self.salesperson_required:
            permissions.append(IsSalesPerson())
        return permissions
