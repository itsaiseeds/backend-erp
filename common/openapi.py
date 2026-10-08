"""Project drf-spectacular schema class.

Groups operations into the Swagger tags declared in :mod:`common.openapi_tags`
instead of drf-spectacular's default (the first URL segment: ``api`` /
``android``). Only the documentation changes; routes are untouched.
"""

from __future__ import annotations

import re

from drf_spectacular.openapi import AutoSchema

from common.openapi_tags import tags_for_path


class GroupedAutoSchema(AutoSchema):
    """``AutoSchema`` whose default tags come from :data:`ROUTE_TAGS`.

    An explicit ``@extend_schema(tags=...)`` on a view still wins. A path no rule
    covers falls back to drf-spectacular's default tag (and is caught by
    ``tests/test_openapi_tags.py``).
    """

    def get_tags(self) -> list[str]:
        tags = tags_for_path(self.path)
        return list(tags) if tags is not None else super().get_tags()

    def get_operation(self, *args, **kwargs):
        """Keep operationIds unique when a later Android version inherits a view.

        A v1 view served under ``/android/api/v2/`` would repeat its
        ``android_api_v1_...`` id (generated or set with ``extend_schema``), so
        the version segment is rewritten to the one in the path. Done on the
        finished operation because an explicit ``operation_id`` bypasses
        ``get_operation_id``.
        """
        operation = super().get_operation(*args, **kwargs)
        match = re.match(r"/android/api/(v\d+)/", self.path)
        if operation and match and "operationId" in operation:
            version = match.group(1)
            operation["operationId"] = re.sub(
                r"^android_api_v\d+_", f"android_api_{version}_", operation["operationId"]
            )
        return operation
