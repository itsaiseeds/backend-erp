"""Mark notifications read: ``POST /android/api/v1/notification/<id>/read`` and
``POST /android/api/v1/notifications/read-all``.

Both only ever touch the caller's own notifications; another user's id reads as
unknown (404). Marking an already-read notification read is not an error.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from aggregator.models import Notification
from aggregator.NotificationOperations import mark_read
from android.api.base import AndroidSharedView


class MarkNotificationReadView(AndroidSharedView):
    """Mark one of the caller's notifications read."""

    @extend_schema(
        summary="Mark one notification read",
        request=None,
        responses={204: {"description": "Marked read."}, 404: {"description": "Unknown id."}},
    )
    def post(self, request: Request, id: int) -> Response:
        get_object_or_404(Notification, pk=id, recipient=request.user)
        mark_read(request.user.pk, id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarkAllNotificationsReadView(AndroidSharedView):
    """Mark every notification of the caller's read."""

    @extend_schema(
        summary="Mark all my notifications read",
        request=None,
        responses={204: {"description": "All marked read."}},
    )
    def post(self, request: Request) -> Response:
        mark_read(request.user.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
