"""API layer for the sales admin website. Session-only; never touches tokens.

Namespace layout
----------------
* ``/api/sales_admin/...`` : the sales admin website (TOTP login, admin /
  sales-person management, logout).
* ``/api/utilities/...``   : session-authenticated web helpers/look-ups.

The sales-person Android app is a separate Django app and is token-only; see
``android`` (served at ``/android/api/<version>/...``).
"""

default_app_config = "api.apps.ApiConfig"
