"""Logout endpoint: revoke the caller's credentials.

``POST /api/sales_admin/auth/logout`` invalidates whichever credential the
caller used to authenticate:

* The bearer token row (if any) is deleted, so the Android app's saved
  ``Token`` header stops working immediately.
* The Django session is flushed and the ``sessionid`` / ``csrftoken`` cookies
  are cleared, so the Flutter admin site's cookie stops working immediately.

Both happen every time — a user with both a session and a token gets both
invalidated. Successful logout returns ``204``.
"""

from __future__ import annotations

from django.contrib.auth import logout
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import ExpiringTokenAuthentication, SessionAuthentication


class LogoutView(APIView):
    """Revoke the caller's session cookie and bearer token."""

    authentication_classes: list[type] = [
        SessionAuthentication,
        ExpiringTokenAuthentication,
    ]
    permission_classes: list[type] = [IsAuthenticated]

    @extend_schema(
        summary="Revoke the caller's credentials",
        request=None,
        responses={
            204: {"description": "Credentials revoked."},
            401: {"description": "Missing or invalid credentials."},
        },
    )
    def post(self, request):
        # Delete + logout under one transaction so a crash between them
        # leaves neither credential half-alive.
        with transaction.atomic():
            Token.objects.filter(user=request.user).delete()
            # ``logout`` also flushes the session store row and clears
            # request.session, so the sessionid cookie stops resolving on
            # the next request.
            logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
