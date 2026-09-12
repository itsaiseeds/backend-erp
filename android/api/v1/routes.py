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
from .CreateMultiSelectBagOrderView import CreateMultiSelectBagOrderView
from .GetClientsView import GetClientsView
from .GetClientView import GetClientView
from .LoginView import LoginView
from .LogoutView import LogoutView
from .ReauthenticateView import ReauthenticateView
from .SalesPersonCatalogueView import SalesPersonCatalogueView
from .StatesView import StatesView
from .UpdateClientView import UpdateClientView

ROUTES: dict[str, type] = {
    "auth/login": LoginView,
    "auth/logout": LogoutView,
    "auth/reauthenticate": ReauthenticateView,
    "utilities/countries": CountriesView,
    "utilities/states": StatesView,
    "utilities/cities": CitiesView,
    "utilities/client-addresses": ClientAddressesView,
    "utilities/client-transport-agencies": ClientTransportAgenciesView,
    "get-clients": GetClientsView,
    "client/<public_id>": GetClientView,
    "create-client": CreateClientView,
    "update-client": UpdateClientView,
    "sales-person-catalogue": SalesPersonCatalogueView,
    "create-multi-select-bag-order": CreateMultiSelectBagOrderView,
}
