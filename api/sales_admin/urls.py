"""Sales admin website routes.

Every pre-auth endpoint (e.g. TOTP login) needs no permission and subclasses a
plain ``APIView``. Protected endpoints with views gated by the admin base view
(e.g. TOTP enrollment) are added here under their own paths.
"""

from django.urls import path

from .TOTPEnrollView import TOTPEnrollView, VerifyTOTPEnrollView
from .VerifyOTPView import VerifyOTPView

urlpatterns = [
    path("auth/otp/verify", VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/totp/enroll", TOTPEnrollView.as_view(), name="totp-enroll"),
    path("auth/totp/verify-enroll", VerifyTOTPEnrollView.as_view(), name="totp-verify-enroll"),
]
