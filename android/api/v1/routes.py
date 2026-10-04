"""Routes introduced at Android API v1.

See ``android.api.routing`` for how this dict is merged across versions: a
route defined here is served by every later version too, unless that version
declares the same key in its own ``ROUTES``.
"""

from __future__ import annotations

from .AnalyticsView import AnalyticsView
from .CitiesView import CitiesView
from .ClientAddressesView import ClientAddressesView
from .ClientTransportAgenciesView import ClientTransportAgenciesView
from .CountriesView import CountriesView
from .CreateClientView import CreateClientView
from .CreateFarmerVisitView import CreateFarmerVisitView
from .CreateFieldTripView import CreateFieldTripView
from .CreateMultiSelectBagOrderView import CreateMultiSelectBagOrderView
from .CropsView import CropsView
from .DeleteFieldTripView import DeleteFieldTripView
from .EndFieldTripView import EndFieldTripView
from .GetChallansView import GetChallansView
from .GetChallanView import GetChallanView
from .GetClientsView import GetClientsView
from .GetClientView import GetClientView
from .GetFieldTripFarmerVisitsView import GetFieldTripFarmerVisitsView
from .GetFieldTripsView import GetFieldTripsView
from .GetNotificationsView import GetNotificationsView
from .GetOrdersView import GetOrdersView
from .GetReturnOrdersView import GetReturnOrdersView
from .GodownCheckTodaysInventoryView import GodownCheckTodaysInventoryView
from .GodownExportInventorySnapshotsView import GodownExportInventorySnapshotsView
from .GodownInwardOtherMaterialsView import GodownInwardOtherMaterialsView
from .GodownInwardRawMaterialsView import GodownInwardRawMaterialsView
from .GodownOtherMaterialRecipesView import GodownOtherMaterialRecipesView
from .GodownOtherMaterialStockView import GodownOtherMaterialStockView
from .GodownRawMaterialStockView import GodownRawMaterialStockView
from .GodownUpdateBagStockView import GodownUpdateBagStockView
from .GodownUpdateSamplePacketStockView import GodownUpdateSamplePacketStockView
from .LoginView import LoginView
from .LogoutView import LogoutView
from .MarkNotificationsReadView import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
)
from .OtherMaterialTypesView import OtherMaterialTypesView
from .PartiesView import PartiesView
from .ProductsView import ProductsView
from .ReauthenticateView import ReauthenticateView
from .RegisterDeviceView import RegisterDeviceView
from .ReturnOrderView import ReturnOrderView
from .SalesAdminsView import SalesAdminsView
from .SalesPersonCatalogueView import SalesPersonCatalogueView
from .StartFieldTripView import StartFieldTripView
from .StatesView import StatesView
from .UpdateClientView import UpdateClientView
from .UpdateFarmerVisitView import UpdateFarmerVisitView
from .UpdateFieldTripView import UpdateFieldTripView
from .UpdateGodownInwardOtherMaterialView import UpdateGodownInwardOtherMaterialView
from .UpdateGodownInwardRawMaterialView import UpdateGodownInwardRawMaterialView

ROUTES: dict[str, type] = {
    "auth/login": LoginView,
    "auth/logout": LogoutView,
    "auth/reauthenticate": ReauthenticateView,
    "utilities/countries": CountriesView,
    "utilities/states": StatesView,
    "utilities/cities": CitiesView,
    "utilities/client-addresses": ClientAddressesView,
    "utilities/client-transport-agencies": ClientTransportAgenciesView,
    "utilities/crops": CropsView,
    "utilities/products": ProductsView,
    "utilities/parties": PartiesView,
    "utilities/other-material-types": OtherMaterialTypesView,
    "utilities/sales-admins": SalesAdminsView,
    "analytics": AnalyticsView,
    "devices/register": RegisterDeviceView,
    "notifications": GetNotificationsView,
    "notifications/read-all": MarkAllNotificationsReadView,
    "notification/<int:id>/read": MarkNotificationReadView,
    "get-clients": GetClientsView,
    "get-orders": GetOrdersView,
    "get-challans": GetChallansView,
    "get-challan/<order_public_id>": GetChallanView,
    "return-order/<order_public_id>": ReturnOrderView,
    "get-return-orders": GetReturnOrdersView,
    "client/<public_id>": GetClientView,
    "create-client": CreateClientView,
    "update-client": UpdateClientView,
    "sales-person-catalogue": SalesPersonCatalogueView,
    "create-multi-select-bag-order": CreateMultiSelectBagOrderView,
    "create-field-trip": CreateFieldTripView,
    "get-field-trips": GetFieldTripsView,
    "edit-field-trip/<public_id>": UpdateFieldTripView,
    "start-field-trip/<public_id>": StartFieldTripView,
    "end-field-trip/<public_id>": EndFieldTripView,
    "delete-field-trip/<public_id>": DeleteFieldTripView,
    "field-trip-farmer-visits/<public_id>": GetFieldTripFarmerVisitsView,
    "create-farmer-visit": CreateFarmerVisitView,
    "edit-farmer-visit/<public_id>": UpdateFarmerVisitView,
    "godown/raw-material-stock": GodownRawMaterialStockView,
    "godown/other-material-stock": GodownOtherMaterialStockView,
    "godown/inward-raw-materials": GodownInwardRawMaterialsView,
    "godown/inward-raw-material/<public_id>": UpdateGodownInwardRawMaterialView,
    "godown/inward-other-materials": GodownInwardOtherMaterialsView,
    "godown/inward-other-material/<public_id>": UpdateGodownInwardOtherMaterialView,
    "godown/other-material-recipes": GodownOtherMaterialRecipesView,
    "godown/check-todays-inventory": GodownCheckTodaysInventoryView,
    "godown/export/inventory-snapshots": GodownExportInventorySnapshotsView,
    "godown/update-bag-stock": GodownUpdateBagStockView,
    "godown/update-sample-packet-stock": GodownUpdateSamplePacketStockView,
}
