"""Routes introduced at Android API v1.

See ``android.api.routing`` for how this dict is merged across versions: a
route defined here is served by every later version too, unless that version
declares the same key in its own ``ROUTES``.
"""

from __future__ import annotations

from .CitiesView import CitiesView
from .CreateClientView import CreateClientView
from .GetClientsView import GetClientsView
from .LoginView import LoginView
from .LogoutView import LogoutView
from .ReauthenticateView import ReauthenticateView
from .UpdateClientView import UpdateClientView

ROUTES: dict[str, type] = {
    "auth/login": LoginView,
    "auth/logout": LogoutView,
    "auth/reauthenticate": ReauthenticateView,
    "utilities/cities": CitiesView,
    "get-clients": GetClientsView,
    "create-client": CreateClientView,
    "update-client": UpdateClientView,
}
