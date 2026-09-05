"""Logout endpoint: revoke the caller's session.

``POST /api/sales-admin/auth/logout`` flushes the Django session and clears
the ``sessionid`` / ``csrftoken`` cookies, so the Flutter admin site's cookie
stops working immediately. Session-only: never touches bearer tokens (see
``android.api.v1.LogoutView`` for the Android counterpart).

Successful logout returns ``204``.
"""

from __future__ import annotations

from django.contrib.auth import logout
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from api.admin import AdminApiView


class LogoutView(AdminApiView):
    """Revoke the caller's session cookie."""

    @extend_schema(
        summary="Revoke the caller's session",
        request=None,
        responses={
            204: {"description": "Session revoked."},
            401: {"description": "Missing or invalid session."},
        },
    )
    def post(self, request):
        # ``logout`` flushes the session store row and clears request.session,
        # so the sessionid cookie stops resolving on the next request.
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
