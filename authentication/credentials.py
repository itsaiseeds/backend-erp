"""Revoking a user's live credentials: web sessions and Android bearer tokens.

Called whenever something a credential was granted on stops being true -- the
user is deactivated, loses a role, changes the phone number they log in with,
or has their TOTP secret rotated (see :meth:`authentication.models.User.save`
and ``guard_soft_delete`` on the ``Admin`` / ``SalesPerson`` profiles). The
user must then log in again, and the login views re-check everything.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.authtoken.models import Token

if TYPE_CHECKING:
    from authentication.models.User import User


def revoke_user_credentials(user: User) -> None:
    """Delete every bearer token and every live web session of ``user``.

    Sessions live in the database backend and store the user id only inside
    the encoded ``session_data``, so the live ones are decoded and matched on
    ``_auth_user_id``. The table only holds unexpired 24h sessions of a few
    staff, so the scan is cheap.
    """
    Token.objects.filter(user=user).delete()

    user_id = str(user.pk)
    session_keys = [
        session.session_key
        for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator()
        if session.get_decoded().get(SESSION_KEY) == user_id
    ]
    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()
