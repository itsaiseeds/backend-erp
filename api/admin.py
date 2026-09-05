"""Base view for the sales admin website.

Admin views authenticate via the browser session cookie only
(``SessionAuthentication``) -- the web side never touches bearer tokens (see
``android.api.base.AndroidBaseView`` for the Android app's token-only
counterpart). Role is expressed per-view via ``BaseApiView``'s flags
(``admin_required`` / ``superuser_required``); this base does not assume one.
"""

from __future__ import annotations

from .authentication import SessionAuthentication
from .views import BaseApiView


class AdminApiView(BaseApiView):
    """Base for every sales admin website endpoint.

    - Authenticates via the browser session only (no token needed).
    - Requires an authenticated user by default (``auth_required = True``,
      inherited from ``BaseApiView``); set ``admin_required = True`` or
      ``superuser_required = True`` on a subclass to further restrict.
    """

    authentication_classes = [SessionAuthentication]
