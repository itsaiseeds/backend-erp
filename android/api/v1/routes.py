"""Routes introduced at Android API v1.

See ``android.api.routing`` for how this dict is merged across versions: a
route defined here is served by every later version too, unless that version
declares the same key in its own ``ROUTES``.
"""

from __future__ import annotations

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
from .GetClientsView import GetClientsView
from .GetClientView import GetClientView
from .GetFieldTripFarmerVisitsView import GetFieldTripFarmerVisitsView
from .GetFieldTripsView import GetFieldTripsView
from .GetOrdersView import GetOrdersView
from .LoginView import LoginView
from .LogoutView import LogoutView
from .ProductsView import ProductsView
from .ReauthenticateView import ReauthenticateView
from .SalesPersonCatalogueView import SalesPersonCatalogueView
from .StartFieldTripView import StartFieldTripView
from .StatesView import StatesView
from .UpdateClientView import UpdateClientView
from .UpdateFieldTripView import UpdateFieldTripView

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
    "get-clients": GetClientsView,
    "get-orders": GetOrdersView,
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
}
