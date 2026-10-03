from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class PushDevice(TimeStampedModel):
    """One installed copy of the Android app, reachable by an FCM token.

    The token is unique: a phone that logs in as someone else re-registers the
    same token, which moves it to the new user. ``updated_at`` doubles as "last
    seen" -- the app re-registers on every login and token refresh.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="user",
        on_delete=models.CASCADE,
        related_name="push_devices",
    )
    fcm_token = models.CharField("FCM token", max_length=512, unique=True)
    app_version = models.CharField("app version", max_length=32, blank=True)

    class Meta:
        verbose_name = "push device"
        verbose_name_plural = "push devices"

    def __str__(self):
        return f"{self.user_id}: {self.fcm_token[:12]}..."
