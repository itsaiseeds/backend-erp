from datetime import timedelta

from django.db import models

from common.models import TimeStampedModel, indian_now

OTP_LIFETIME_MINUTES = 5


class MobileVerification(TimeStampedModel):
    """Stores an OTP used to log in (or verify) a user.

    An OTP is valid for a short window (default 5 minutes) after generation,
    regardless of whether it is for a SalesPerson, an Admin, or a superuser.
    """

    user = models.ForeignKey(
        "authentication.User",
        on_delete=models.CASCADE,
        related_name="mobile_verifications",
        db_index=True,
    )
    phone_number = models.CharField(max_length=10, editable=False, db_index=True)
    otp = models.CharField("OTP", max_length=8)
    is_used = models.BooleanField(default=False)

    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = "mobile verification"
        verbose_name_plural = "mobile verifications"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.phone_number and self.user_id:
            self.phone_number = self.user.phone_number
        if not self.expires_at:
            self.expires_at = indian_now() + timedelta(minutes=OTP_LIFETIME_MINUTES)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return indian_now() > self.expires_at

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=["is_used"])

    def __str__(self):
        state = "used" if self.is_used else ("expired" if self.is_expired else "pending")
        return f"OTP for {self.phone_number} ({state})"
