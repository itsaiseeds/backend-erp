"""Sales admin website routes.

Every pre-auth endpoint (e.g. TOTP login) needs no permission and subclasses a
plain ``APIView``.
"""

from django.urls import path

from .AdminsView import AdminsView
from .CheckTodaysInventoryView import CheckTodaysInventoryView
from .CropsView import CropsView
from .LogoutView import LogoutView
from .ProductPackagingsView import ProductPackagingsView
from .ProductsView import ProductsView
from .SalesPeopleView import SalesPeopleView
from .StockView import StockView
from .UpdateAdminView import UpdateAdminView
from .UpdateCropView import UpdateCropView
from .UpdateProductPackagingView import UpdateProductPackagingView
from .UpdateProductView import UpdateProductView
from .UpdateSalesPersonView import UpdateSalesPersonView
from .UpdateTodaysInventoryView import UpdateTodaysInventoryView
from .VerifyOTPView import VerifyOTPView

urlpatterns = [
    path("auth/otp/verify", VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/logout", LogoutView.as_view(), name="logout"),
    path("admins", AdminsView.as_view(), name="admins"),
    path("admins/<int:id>", UpdateAdminView.as_view(), name="update-admin"),
    path("crops", CropsView.as_view(), name="crops"),
    path("crops/<int:id>", UpdateCropView.as_view(), name="update-crop"),
    path(
        "check-todays-inventory",
        CheckTodaysInventoryView.as_view(),
        name="check-todays-inventory",
    ),
    path(
        "update-todays-inventory",
        UpdateTodaysInventoryView.as_view(),
        name="update-todays-inventory",
    ),
    path("get-stock/<str:public_id>", StockView.as_view(), name="get-stock"),
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
]
