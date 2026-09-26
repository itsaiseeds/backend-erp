"""Project drf-spectacular schema class.

Groups operations into the Swagger tags declared in :mod:`common.openapi_tags`
instead of drf-spectacular's default (the first URL segment: ``api`` /
``android``). Only the documentation changes; routes are untouched.
"""

from __future__ import annotations

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
