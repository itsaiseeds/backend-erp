"""API layer.

All HTTP endpoints live under ``/api/``.

Namespace layout
----------------
* ``/api/auth/...``      : shared authentication endpoints (both clients).
* ``/api/admin/...``     : the admin-facing Flutter web app.
* ``/api/android/<v>/...``: the sales-person-facing Android app. ``<v>`` is a
  major version bumped only on breaking changes (e.g. ``v1``).
"""

default_app_config = "api.apps.ApiConfig"
