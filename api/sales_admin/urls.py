"""Sales admin website routes.

Every pre-auth endpoint (e.g. TOTP login) needs no permission and subclasses a
plain ``APIView``.
"""

from django.urls import path

from .VerifyOTPView import VerifyOTPView

urlpatterns = [
    path("auth/otp/verify", VerifyOTPView.as_view(), name="verify-otp"),
]
