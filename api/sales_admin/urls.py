"""Sales admin website routes.

Every pre-auth endpoint (e.g. TOTP login) needs no permission and subclasses a
plain ``APIView``.
"""

from django.urls import path

from .AdminsView import AdminsView
from .SalesPeopleView import SalesPeopleView
from .UpdateAdminView import UpdateAdminView
from .UpdateSalesPersonView import UpdateSalesPersonView
from .VerifyOTPView import VerifyOTPView

urlpatterns = [
    path("auth/otp/verify", VerifyOTPView.as_view(), name="verify-otp"),
    path("admins", AdminsView.as_view(), name="admins"),
    path("admins/<int:pk>", UpdateAdminView.as_view(), name="update-admin"),
    path("sales-people", SalesPeopleView.as_view(), name="sales-people"),
    path(
        "sales-people/<int:pk>",
        UpdateSalesPersonView.as_view(),
        name="update-sales-person",
    ),
]
