"""Sales admin website routes.

Every pre-auth endpoint (e.g. TOTP login) needs no permission and subclasses a
plain ``APIView``.
"""

from django.urls import path

from .AdminsView import AdminsView
from .CheckTodaysInventoryView import CheckTodaysInventoryView
from .CropsView import CropsView
from .DeleteOtherMaterialRecipeView import DeleteOtherMaterialRecipeView
from .DispatchOrderView import DispatchOrderView
from .GetClientsView import GetClientsView
from .GetClientView import GetClientView
from .GetDispatchChallansView import GetDispatchChallansView
from .GetOrdersView import GetOrdersView
from .GetOrderView import GetOrderView
from .HoldOrderView import HoldOrderView
from .InwardOtherMaterialsView import InwardOtherMaterialsView
from .InwardRawMaterialsView import InwardRawMaterialsView
from .LogoutView import LogoutView
from .LooseStockView import LooseStockView
from .OtherMaterialRecipesView import OtherMaterialRecipesView
from .OtherMaterialStockView import OtherMaterialStockView
from .OtherMaterialTypesView import OtherMaterialTypesView
from .PartiesView import PartiesView
from .ProductPackagingsView import ProductPackagingsView
from .ProductsView import ProductsView
from .RawMaterialStockView import RawMaterialStockView
from .RejectOrderView import RejectOrderView
from .RevertDispatchView import RevertDispatchView
from .SalesPeopleView import SalesPeopleView
from .StockView import StockView
from .UnverifyOrderView import UnverifyOrderView
from .UpdateAdminView import UpdateAdminView
from .UpdateClientView import UpdateClientView
from .UpdateCropView import UpdateCropView
from .UpdateInwardOtherMaterialView import UpdateInwardOtherMaterialView
from .UpdateInwardRawMaterialView import UpdateInwardRawMaterialView
from .UpdateLooseStockView import UpdateLooseStockView
from .UpdateOrderView import UpdateOrderView
from .UpdateOtherMaterialTypeView import UpdateOtherMaterialTypeView
from .UpdatePartyView import UpdatePartyView
from .UpdateProductPackagingView import UpdateProductPackagingView
from .UpdateProductView import UpdateProductView
from .UpdateSalesPersonView import UpdateSalesPersonView
from .UpdateTodaysInventoryView import UpdateTodaysInventoryView
from .UploadLRNumberView import UploadLRNumberView
from .VerifyClientView import VerifyClientView
from .VerifyOrderView import VerifyOrderView
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
    # Order routes follow the same convention: ``orders/`` is a collection and
    # ``order/<public_id>`` a collection item, while the lifecycle verbs carry
    # the id in the path because each acts on one named order.
    path("orders/", GetOrdersView.as_view(), name="orders"),
    path("order/<str:public_id>", GetOrderView.as_view(), name="order-detail"),
    path("edit-order/<str:public_id>", UpdateOrderView.as_view(), name="edit-order"),
    path("verify-order/<str:public_id>", VerifyOrderView.as_view(), name="verify-order"),
    path(
        "unverify-order/<str:public_id>",
        UnverifyOrderView.as_view(),
        name="unverify-order",
    ),
    path(
        "dispatch-order/<str:public_id>",
        DispatchOrderView.as_view(),
        name="dispatch-order",
    ),
    path(
        "upload-lr-number/<str:public_id>",
        UploadLRNumberView.as_view(),
        name="upload-lr-number",
    ),
    path(
        "revert-dispatch/<str:public_id>",
        RevertDispatchView.as_view(),
        name="revert-dispatch",
    ),
    # A collection, like ``orders/`` above -- hence the trailing slash.
    path(
        "dispatch-challans/",
        GetDispatchChallansView.as_view(),
        name="dispatch-challans",
    ),
    path("hold-order/<str:public_id>", HoldOrderView.as_view(), name="hold-order"),
    path("reject-order/<str:public_id>", RejectOrderView.as_view(), name="reject-order"),
    # Inward movement: master data, bookings, recipe and stock positions. The
    # lookups (parties, other-material-types) are id-addressed like ``crops``;
    # the bookable rows (inward-raw-material, inward-other-material) and recipes
    # are public-id-addressed like ``products``.
    path("parties", PartiesView.as_view(), name="parties"),
    path("parties/<int:id>", UpdatePartyView.as_view(), name="update-party"),
    path(
        "other-material-types",
        OtherMaterialTypesView.as_view(),
        name="other-material-types",
    ),
    path(
        "other-material-types/<int:id>",
        UpdateOtherMaterialTypeView.as_view(),
        name="update-other-material-type",
    ),
    path(
        "other-material-recipes",
        OtherMaterialRecipesView.as_view(),
        name="other-material-recipes",
    ),
    path(
        "other-material-recipe/<str:public_id>",
        DeleteOtherMaterialRecipeView.as_view(),
        name="delete-other-material-recipe",
    ),
    path(
        "inward-raw-materials",
        InwardRawMaterialsView.as_view(),
        name="inward-raw-materials",
    ),
    path(
        "inward-raw-material/<str:public_id>",
        UpdateInwardRawMaterialView.as_view(),
        name="update-inward-raw-material",
    ),
    path(
        "inward-other-materials",
        InwardOtherMaterialsView.as_view(),
        name="inward-other-materials",
    ),
    path(
        "inward-other-material/<str:public_id>",
        UpdateInwardOtherMaterialView.as_view(),
        name="update-inward-other-material",
    ),
    path(
        "raw-material-stock",
        RawMaterialStockView.as_view(),
        name="raw-material-stock",
    ),
    path(
        "other-material-stock",
        OtherMaterialStockView.as_view(),
        name="other-material-stock",
    ),
]
