"""Sales admin website routes.

Every pre-auth endpoint (e.g. TOTP login) needs no permission and subclasses a
plain ``APIView``.
"""

from django.urls import path

from .AdminsView import AdminsView
from .CheckTodaysInventoryView import CheckTodaysInventoryView
from .CropsView import CropsView
from .GetClientsView import GetClientsView
from .GetClientView import GetClientView
from .LogoutView import LogoutView
from .LooseStockView import LooseStockView
from .ProductPackagingsView import ProductPackagingsView
from .ProductsView import ProductsView
from .SalesPeopleView import SalesPeopleView
from .StockView import StockView
from .UpdateAdminView import UpdateAdminView
from .UpdateClientView import UpdateClientView
from .UpdateCropView import UpdateCropView
from .UpdateLooseStockView import UpdateLooseStockView
from .UpdateProductPackagingView import UpdateProductPackagingView
from .UpdateProductView import UpdateProductView
from .UpdateSalesPersonView import UpdateSalesPersonView
from .UpdateTodaysInventoryView import UpdateTodaysInventoryView
from .VerifyClientView import VerifyClientView
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
    path(
        "update-loose-stock",
        UpdateLooseStockView.as_view(),
        name="update-loose-stock",
    ),
    path("loose-stock", LooseStockView.as_view(), name="loose-stock"),
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
    # The client *verb* routes keep a trailing slash; ``client/<public_id>`` is
    # a collection item, named like ``products/<public_id>`` above.
    path("verify-client/", VerifyClientView.as_view(), name="verify-client"),
    path("update-client/", UpdateClientView.as_view(), name="update-client"),
    path("get-clients/", GetClientsView.as_view(), name="get-clients"),
    path("client/<str:public_id>", GetClientView.as_view(), name="client-detail"),
]
