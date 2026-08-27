"""Sales admin website routes.

Every pre-auth endpoint (e.g. OTP) needs no permission and subclasses a plain
``APIView``. Protected endpoints with views gated by the admin base view are
added here under their own paths.
"""

from django.urls import path

from .GenerateOTPView import GenerateOTPView
from .VerifyOTPView import VerifyOTPView

urlpatterns = [
    path("auth/otp/request", GenerateOTPView.as_view(), name="generate-otp"),
    path("auth/otp/verify", VerifyOTPView.as_view(), name="verify-otp"),
]
