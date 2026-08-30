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
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .authentication import ExpiringTokenAuthentication
from .permissions import IsAdminUser, IsSuperUser


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

    The concrete client bases (:class:`~api.admin.AdminApiView` and
    :class:`~api.android.AndroidBaseView`) fix which *credentials* authenticate
    a request (session cookie vs. bearer token). This class only combines the
    role flags into ready-made permission checks.
    """

    auth_required = True
    admin_required = False
    superuser_required = False

    authentication_classes = [SessionAuthentication, ExpiringTokenAuthentication]

    def get_permissions(self):
        permissions = []
        if self.auth_required:
            permissions.append(IsAuthenticated())
        if self.admin_required:
            permissions.append(IsAdminUser())
        if self.superuser_required:
            permissions.append(IsSuperUser())
        return permissions
