"""Base view for the sales admin website.

Admin views authenticate via the browser session cookie (``SessionAuthentication``)
and demand an application ``Admin`` profile. Set ``superuser_required = True``
on a subclass to additionally require a Django superuser.
"""

from __future__ import annotations

from .authentication import SessionAuthentication
from .views import BaseApiView


class AdminApiView(BaseApiView):
    """Base for every sales admin website endpoint.

    - Authenticates via the browser session (no token needed).
    - Requires an authenticated user with an application ``Admin`` profile
      (``admin_required`` is ``True`` by default here).
    - Set ``superuser_required = True`` to restrict to superusers.
    """

    authentication_classes = [SessionAuthentication]
    admin_required = True
