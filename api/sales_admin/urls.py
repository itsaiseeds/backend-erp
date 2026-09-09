"""Sales admin website routes.

Every pre-auth endpoint (e.g. TOTP login) needs no permission and subclasses a
plain ``APIView``.
"""

from django.urls import path

from .AdminsView import AdminsView
from .CropsView import CropsView
from .GetClientsView import GetClientsView
from .LogoutView import LogoutView
from .ProductPackagingsView import ProductPackagingsView
from .ProductsView import ProductsView
from .SalesPeopleView import SalesPeopleView
from .UpdateAdminView import UpdateAdminView
from .UpdateClientView import UpdateClientView
from .UpdateCropView import UpdateCropView
from .UpdateProductPackagingView import UpdateProductPackagingView
from .UpdateProductView import UpdateProductView
from .UpdateSalesPersonView import UpdateSalesPersonView
from .VerifyClientView import VerifyClientView
from .VerifyOTPView import VerifyOTPView

urlpatterns = [
    path("auth/otp/verify", VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("admins", AdminsView.as_view(), name="admins"),
    path("admins/<int:id>", UpdateAdminView.as_view(), name="update-admin"),
    path("crops", CropsView.as_view(), name="crops"),
    path("crops/<int:id>", UpdateCropView.as_view(), name="update-crop"),
    path("products", ProductsView.as_view(), name="products"),
    path("products/<str:public_id>", UpdateProductView.as_view(), name="update-product"),
    path("product-packagings", ProductPackagingsView.as_view(), name="product-packagings"),
    path(
        "product-packagings/<str:public_id>",
        UpdateProductPackagingView.as_view(),
        name="update-product-packaging",
    ),
    path("sales-people", SalesPeopleView.as_view(), name="sales-people"),
    path(
        "sales-people/<int:id>",
        UpdateSalesPersonView.as_view(),
        name="update-sales-person",
    ),
    # The client routes are verbs, not collections, and keep a trailing slash.
    path("verify-client/", VerifyClientView.as_view(), name="verify-client"),
    path("update-client/", UpdateClientView.as_view(), name="update-client"),
    path("get-clients/", GetClientsView.as_view(), name="get-clients"),
]
