"""``/sales-admin/<path>``: the Flutter build is served, and nothing outside it.

The build dir is a throwaway tree under a temp ``BASE_DIR`` holding one asset,
``index.html`` and -- *outside* the build dir -- a secret file every traversal
attempt aims at.

Run: bash scripts/run.sh test-unit tests/test_flutter_catch_all.py
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

SECRET = b"SECRET_KEY=leaked"


class FlutterCatchAllTest(SimpleTestCase):
    """tests/test_flutter_catch_all.py::FlutterCatchAllTest"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_dir = Path(tempfile.mkdtemp())
        build_dir = cls.base_dir / "admin_saiseeds" / "build" / "web"
        (build_dir / "assets").mkdir(parents=True)
        (build_dir / "index.html").write_bytes(b"<html>app</html>")
        (build_dir / "assets" / "main.js").write_bytes(b"console.log(1)")
        cls.secret = cls.base_dir / "secret.env"
        cls.secret.write_bytes(SECRET)
        cls.enterClassContext(override_settings(BASE_DIR=cls.base_dir))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base_dir)
        super().tearDownClass()

    def _body(self, resp) -> bytes:
        return b"".join(resp.streaming_content) if resp.streaming else resp.content

    def test_build_files_are_served_with_their_content_type(self):
        """tests/test_flutter_catch_all.py::FlutterCatchAllTest::test_build_files_are_served_with_their_content_type"""
        resp = self.client.get("/sales-admin/assets/main.js")

        self.assertEqual(resp.status_code, 200)
        self.assertIn("javascript", resp["Content-Type"])
        self.assertEqual(self._body(resp), b"console.log(1)")

    def test_unknown_routes_fall_back_to_index_html(self):
        """tests/test_flutter_catch_all.py::FlutterCatchAllTest::test_unknown_routes_fall_back_to_index_html"""
        for url in ("/sales-admin", "/sales-admin/", "/sales-admin/orders/42"):
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(self._body(resp), b"<html>app</html>")

    def test_paths_escaping_the_build_dir_are_refused(self):
        """tests/test_flutter_catch_all.py::FlutterCatchAllTest::test_paths_escaping_the_build_dir_are_refused"""
        # secret.env sits three levels above build/web.
        for url in (
            f"/sales-admin/{self.secret.as_posix()}",  # //abs/path/secret.env
            "/sales-admin/../../../secret.env",
            "/sales-admin/..%2F..%2F..%2Fsecret.env",
            "/sales-admin/%2e%2e%2f%2e%2e%2f%2e%2e%2fsecret.env",
            "/sales-admin/assets/../../../../secret.env",
        ):
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 404)
                self.assertNotIn(SECRET, self._body(resp))
