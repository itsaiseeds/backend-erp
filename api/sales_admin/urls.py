"""Sales admin website routes.

Every pre-auth endpoint (e.g. TOTP login) needs no permission and subclasses a
plain ``APIView``.
"""

from django.urls import path

from .AcceptReturnOrderView import AcceptReturnOrderView
from .AdminsView import AdminsView
from .ApproveFieldTripView import ApproveFieldTripView
from .BagStockView import BagStockView
from .CheckTodaysInventoryView import CheckTodaysInventoryView
from .CreateCustomOrderView import CreateCustomOrderView
from .CropsView import CropsView
from .CustomOrderView import CustomOrderView
from .DeleteOtherMaterialRecipeView import DeleteOtherMaterialRecipeView
from .DispatchCustomOrderView import DispatchCustomOrderView
from .DispatchOrderView import DispatchOrderView
from .ExportCustomOrdersView import ExportCustomOrdersView
from .ExportDispatchReceiptsView import ExportDispatchReceiptsView
from .ExportInventorySnapshotsView import ExportInventorySnapshotsView
from .ExportInwardEntriesView import ExportInwardEntriesView
from .ExportOrdersView import ExportOrdersView
from .FieldTripView import FieldTripView
from .GetClientsView import GetClientsView
from .GetClientView import GetClientView
from .GetCustomOrdersView import GetCustomOrdersView
from .GetDispatchChallansView import GetDispatchChallansView
from .GetFieldTripFarmerVisitsView import GetFieldTripFarmerVisitsView
from .GetFieldTripsView import GetFieldTripsView
from .GetOrdersView import GetOrdersView
from .GetOrderView import GetOrderView
from .GetReturnOrdersView import GetReturnOrdersView
from .GodownManagersView import GodownManagersView
from .HoldOrderView import HoldOrderView
from .InwardOtherMaterialsView import InwardOtherMaterialsView
from .InwardRawMaterialsView import InwardRawMaterialsView
from .LogoutView import LogoutView
from .OtherMaterialRecipesView import OtherMaterialRecipesView
from .OtherMaterialStockView import OtherMaterialStockView
from .OtherMaterialTypesView import OtherMaterialTypesView
from .PartiesView import PartiesView
from .ProductPackagingsView import ProductPackagingsView
from .ProductStockLedgerView import ProductStockLedgerView
from .ProductsView import ProductsView
from .RawMaterialStockView import RawMaterialStockView
from .RawMaterialWastesView import RawMaterialWastesView
from .RejectOrderView import RejectOrderView
from .RejectReturnOrderView import RejectReturnOrderView
from .ReturnOrderRecipesView import ReturnOrderRecipesView
from .RevertAcceptReturnOrderView import RevertAcceptReturnOrderView
from .RevertCustomOrderDispatchView import RevertCustomOrderDispatchView
from .RevertDispatchView import RevertDispatchView
from .SalesPeopleView import SalesPeopleView
from .SamplePacketStockView import LooseStockView
from .StockView import StockView
from .UnapproveFieldTripView import UnapproveFieldTripView
from .UnrejectReturnOrderView import UnrejectReturnOrderView
from .UnverifyOrderView import UnverifyOrderView
from .UpdateAdminView import UpdateAdminView
from .UpdateBagStockView import UpdateTodaysInventoryView
from .UpdateClientView import UpdateClientView
from .UpdateCropView import UpdateCropView
from .UpdateCustomOrderView import UpdateCustomOrderView
from .UpdateFieldTripView import UpdateFieldTripView
from .UpdateGodownManagerView import UpdateGodownManagerView
from .UpdateInwardOtherMaterialView import UpdateInwardOtherMaterialView
from .UpdateInwardRawMaterialView import UpdateInwardRawMaterialView
from .UpdateOrderView import UpdateOrderView
from .UpdateOtherMaterialTypeView import UpdateOtherMaterialTypeView
from .UpdatePartyView import UpdatePartyView
from .UpdateProductPackagingView import UpdateProductPackagingView
from .UpdateProductView import UpdateProductView
from .UpdateRawMaterialWasteView import UpdateRawMaterialWasteView
from .UpdateReturnOrderView import UpdateReturnOrderView
from .UpdateSalesPersonView import UpdateSalesPersonView
from .UpdateSamplePacketStockView import UpdateLooseStockView
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
        "update-bag-stock",
        UpdateTodaysInventoryView.as_view(),
        name="update-bag-stock",
    ),
    path(
        "update-sample-packet-stock",
        UpdateLooseStockView.as_view(),
        name="update-sample-packet-stock",
    ),
    path(
        "bag-stock",
        BagStockView.as_view(),
        name="bag-stock",
    ),
    path("sample-packet-stock", LooseStockView.as_view(), name="sample-packet-stock"),
    path("get-stock/<str:public_id>", StockView.as_view(), name="get-stock"),
    path(
        "product-stock-ledger/<str:public_id>",
        ProductStockLedgerView.as_view(),
        name="product-stock-ledger",
    ),
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
    path("godown-managers", GodownManagersView.as_view(), name="godown-managers"),
    path(
        "godown-managers/<int:id>",
        UpdateGodownManagerView.as_view(),
        name="update-godown-manager",
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
    # Returns follow the order convention: ``return-orders/`` is a collection and
    # the verbs carry the id in the path. A return is raised from the Android app
    # (``return-order/<order_public_id>``), so there is no admin create route.
    path("return-orders/", GetReturnOrdersView.as_view(), name="return-orders"),
    path(
        "edit-return-order/<str:public_id>",
        UpdateReturnOrderView.as_view(),
        name="edit-return-order",
    ),
    path(
        "return-order-recipes/<str:public_id>",
        ReturnOrderRecipesView.as_view(),
        name="return-order-recipes",
    ),
    path(
        "accept-return-order/<str:public_id>",
        AcceptReturnOrderView.as_view(),
        name="accept-return-order",
    ),
    path(
        "reject-return-order/<str:public_id>",
        RejectReturnOrderView.as_view(),
        name="reject-return-order",
    ),
    path(
        "unreject-return-order/<str:public_id>",
        UnrejectReturnOrderView.as_view(),
        name="unreject-return-order",
    ),
    path(
        "revert-accept-return-order/<str:public_id>",
        RevertAcceptReturnOrderView.as_view(),
        name="revert-accept-return-order",
    ),
    # Custom (loose-packet) orders mirror the order routes: ``custom-orders/`` is
    # a collection, ``custom-order/<public_id>`` a collection item (GET /
    # DELETE), and the verbs carry the id in the path. Booking is admin-only,
    # hence a sales-admin ``create-custom-order`` rather than an Android route.
    path("custom-orders/", GetCustomOrdersView.as_view(), name="custom-orders"),
    path(
        "create-custom-order",
        CreateCustomOrderView.as_view(),
        name="create-custom-order",
    ),
    path(
        "custom-order/<str:public_id>",
        CustomOrderView.as_view(),
        name="custom-order-detail",
    ),
    path(
        "edit-custom-order/<str:public_id>",
        UpdateCustomOrderView.as_view(),
        name="edit-custom-order",
    ),
    # No upload-lr-number counterpart: a custom order always goes on our
    # own vehicle, so there is no transporter to issue an LR.
    path(
        "dispatch-custom-order/<str:public_id>",
        DispatchCustomOrderView.as_view(),
        name="dispatch-custom-order",
    ),
    path(
        "revert-custom-order-dispatch/<str:public_id>",
        RevertCustomOrderDispatchView.as_view(),
        name="revert-custom-order-dispatch",
    ),
    # Field trips follow the order convention: ``field-trips/`` is a collection,
    # ``field-trip/<public_id>`` a collection item (GET / DELETE), and the verbs
    # carry the id in the path.
    path("field-trips/", GetFieldTripsView.as_view(), name="field-trips"),
    path("field-trip/<str:public_id>", FieldTripView.as_view(), name="field-trip-detail"),
    path(
        "field-trip-farmer-visits/<str:public_id>",
        GetFieldTripFarmerVisitsView.as_view(),
        name="field-trip-farmer-visits",
    ),
    path(
        "edit-field-trip/<str:public_id>",
        UpdateFieldTripView.as_view(),
        name="edit-field-trip",
    ),
    path(
        "approve-field-trip/<str:public_id>",
        ApproveFieldTripView.as_view(),
        name="approve-field-trip",
    ),
    path(
        "unapprove-field-trip/<str:public_id>",
        UnapproveFieldTripView.as_view(),
        name="unapprove-field-trip",
    ),
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
        "raw-material-wastes",
        RawMaterialWastesView.as_view(),
        name="raw-material-wastes",
    ),
    path(
        "raw-material-waste/<str:public_id>",
        UpdateRawMaterialWasteView.as_view(),
        name="update-raw-material-waste",
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
    # -- Date-range exports (api/export_views.py) -------------------------------
    path("export/orders", ExportOrdersView.as_view(), name="export-orders"),
    path(
        "export/custom-orders",
        ExportCustomOrdersView.as_view(),
        name="export-custom-orders",
    ),
    path(
        "export/dispatch-receipts",
        ExportDispatchReceiptsView.as_view(),
        name="export-dispatch-receipts",
    ),
    path(
        "export/inward-entries",
        ExportInwardEntriesView.as_view(),
        name="export-inward-entries",
    ),
    path(
        "export/inventory-snapshots",
        ExportInventorySnapshotsView.as_view(),
        name="export-inventory-snapshots",
    ),
]
