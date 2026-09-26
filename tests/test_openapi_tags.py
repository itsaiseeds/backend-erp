"""Every documented endpoint lands in a declared Swagger group.

The grouping table is ``common.openapi_tags.ROUTE_TAGS``; a new endpoint that
no rule covers would silently fall back to drf-spectacular's default ``api`` /
``android`` tag, so this fails until the table is updated.

tests/test_openapi_tags.py
"""

from __future__ import annotations

from django.test import SimpleTestCase
from drf_spectacular.generators import SchemaGenerator

from common.openapi_tags import OPENAPI_TAGS, tags_for_path


class OpenApiTagsTest(SimpleTestCase):
    """tests/test_openapi_tags.py::OpenApiTagsTest"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = SchemaGenerator().get_schema(request=None, public=True)

    def _operations(self):
        for path, item in self.schema["paths"].items():
            for method, operation in item.items():
                yield path, method, operation

    def test_every_operation_is_in_a_declared_group(self):
        declared = {tag["name"] for tag in OPENAPI_TAGS}
        ungrouped = [
            f"{method.upper()} {path} -> {operation.get('tags')}"
            for path, method, operation in self._operations()
            if not operation.get("tags") or not set(operation["tags"]) <= declared
        ]

        self.assertEqual(ungrouped, [], "Add these paths to ROUTE_TAGS.")

    def test_every_declared_group_is_used(self):
        used = {tag for _, _, operation in self._operations() for tag in operation["tags"]}

        self.assertEqual(
            [tag["name"] for tag in OPENAPI_TAGS if tag["name"] not in used], []
        )

    def test_a_segment_prefix_does_not_match_a_longer_segment(self):
        # ``order`` must not swallow ``orders``' siblings like ``order-x``.
        self.assertIsNone(tags_for_path("/api/sales-admin/order-history"))
