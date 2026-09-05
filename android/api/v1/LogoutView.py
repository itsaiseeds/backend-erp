"""Logout endpoint: revoke the caller's bearer token.

``POST /android/api/v1/auth/logout`` deletes the caller's ``Token`` row, so
the app's saved bearer header stops working immediately. Token-only: never
touches sessions (see ``api.sales_admin.LogoutView`` for the web counterpart,
which flushes a session instead).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from android.api.base import AndroidBaseView


class LogoutView(AndroidBaseView):
    """Revoke the caller's bearer token.

    Logout must succeed for anyone the token authentication accepts, so this
    view relaxes the ``salesperson_required`` gate inherited from
    ``AndroidBaseView``. Otherwise a user whose ``SalesPerson`` profile has
    been soft-deleted (or has already been logged out server-side) would be
    unable to revoke their still-valid token, leaving it live for the rest of
    ``TOKEN_TTL_HOURS``.
    """

    salesperson_required = False

    @extend_schema(
        summary="Revoke the caller's bearer token",
        request=None,
        responses={
            204: {"description": "Token revoked."},
            401: {"description": "Missing or invalid token."},
        },
    )
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
