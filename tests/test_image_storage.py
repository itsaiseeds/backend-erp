"""Unit tests for the image storage package (``common.storage``).

Covers the shared validation, the two backends, and the dispatch between them.
No network is ever touched: ``requests.post`` / ``requests.delete`` are patched,
and the Supabase settings are overridden per test.

Run: bash scripts/run.sh test-unit
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework import serializers

from common.storage import MAX_IMAGE_BYTES, delete_image, upload_image

SUPABASE_CONFIGURED = {
    "SUPABASE_URL": "https://sb.example",
    "SUPABASE_SECRET_KEY": "sb_secret_test",
    "SUPABASE_STORAGE_BUCKET": "product-images",
}

# A legacy ``service_role`` key: three dot-separated base64 segments.
SUPABASE_LEGACY_JWT = {
    **SUPABASE_CONFIGURED,
    "SUPABASE_SECRET_KEY": "header.payload.signature",
}

SUPABASE_UNCONFIGURED = {
    "SUPABASE_URL": "",
    "SUPABASE_SECRET_KEY": "",
    "SUPABASE_STORAGE_BUCKET": "",
}

PUBLIC_PREFIX = "https://sb.example/storage/v1/object/public/product-images/"


def _image(*, content_type="image/png", content=b"pretend-png") -> SimpleUploadedFile:
    return SimpleUploadedFile("pic.png", content, content_type=content_type)


def _path_of(url: str) -> Path:
    """The on-disk location a local-backend URL points at."""
    return Path(settings.MEDIA_ROOT) / url[len(settings.MEDIA_URL):]


@override_settings(**SUPABASE_UNCONFIGURED)
class LocalBackendTest(SimpleTestCase):
    """The disk backend used in development and tests.

    tests/test_image_storage.py::LocalBackendTest
    """

    def test_upload_writes_the_file_under_media_root(self):
        """tests/test_image_storage.py::LocalBackendTest::test_upload_writes_the_file_under_media_root"""
        url = upload_image(_image(content=b"the-bytes"), folder="products")

        self.assertTrue(url.startswith(f"{settings.MEDIA_URL}products/"))
        self.assertTrue(url.endswith(".png"))
        self.assertTrue(_path_of(url).is_file())
        self.assertEqual(_path_of(url).read_bytes(), b"the-bytes")

    def test_no_network_call_is_attempted(self):
        """tests/test_image_storage.py::LocalBackendTest::test_no_network_call_is_attempted"""
        with patch("common.storage.supabase.requests.post") as post:
            upload_image(_image(), folder="products")
        post.assert_not_called()

    def test_each_upload_gets_its_own_file(self):
        """tests/test_image_storage.py::LocalBackendTest::test_each_upload_gets_its_own_file"""
        first = upload_image(_image(), folder="products")
        second = upload_image(_image(), folder="products")
        self.assertNotEqual(first, second)

    def test_delete_removes_the_file(self):
        """tests/test_image_storage.py::LocalBackendTest::test_delete_removes_the_file"""
        url = upload_image(_image(), folder="products")
        self.assertTrue(_path_of(url).is_file())

        delete_image(url)
        self.assertFalse(_path_of(url).exists())

    def test_deleting_a_missing_file_is_harmless(self):
        """tests/test_image_storage.py::LocalBackendTest::test_deleting_a_missing_file_is_harmless"""
        delete_image(f"{settings.MEDIA_URL}products/never-existed.png")  # must not raise

    def test_a_supabase_url_from_another_environment_is_ignored(self):
        """tests/test_image_storage.py::LocalBackendTest::test_a_supabase_url_from_another_environment_is_ignored"""
        with patch("common.storage.supabase.requests.delete") as request_delete:
            delete_image(PUBLIC_PREFIX + "products/a.png")
        request_delete.assert_not_called()


@override_settings(**SUPABASE_CONFIGURED)
class SupabaseBackendTest(SimpleTestCase):
    """The bucket backend used once credentials are present.

    tests/test_image_storage.py::SupabaseBackendTest
    """

    def test_upload_returns_the_public_url_and_writes_nothing_locally(self):
        """tests/test_image_storage.py::SupabaseBackendTest::test_upload_returns_the_public_url_and_writes_nothing_locally"""
        with patch("common.storage.supabase.requests.post") as post:
            post.return_value = Mock(ok=True)
            url = upload_image(_image(), folder="products")

        self.assertTrue(url.startswith(PUBLIC_PREFIX + "products/"))
        self.assertTrue(url.endswith(".png"))
        self.assertTrue(
            post.call_args.args[0].startswith(
                "https://sb.example/storage/v1/object/product-images/products/"
            )
        )
        # An ``sb_secret_…`` key is opaque, not a JWT: it goes in ``apikey``.
        # Sending it as a bearer token makes Storage try to JWT-decode it and
        # answer 403 "Invalid Compact JWS".
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["apikey"], "sb_secret_test")
        self.assertNotIn("Authorization", headers)
        self.assertFalse(Path(settings.MEDIA_ROOT).exists())

    @override_settings(**SUPABASE_LEGACY_JWT)
    def test_a_legacy_jwt_key_is_also_sent_as_a_bearer_token(self):
        """tests/test_image_storage.py::SupabaseBackendTest::test_a_legacy_jwt_key_is_also_sent_as_a_bearer_token"""
        with patch("common.storage.supabase.requests.post") as post:
            post.return_value = Mock(ok=True)
            upload_image(_image(), folder="products")

        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["apikey"], "header.payload.signature")
        self.assertEqual(headers["Authorization"], "Bearer header.payload.signature")

    def test_supabase_error_becomes_a_validation_error(self):
        """tests/test_image_storage.py::SupabaseBackendTest::test_supabase_error_becomes_a_validation_error"""
        with patch("common.storage.supabase.requests.post") as post:
            post.return_value = Mock(ok=False, status_code=500, text="boom")
            with pytest.raises(serializers.ValidationError, match="Could not upload"):
                upload_image(_image(), folder="products")

    def test_delete_targets_the_object_behind_the_public_url(self):
        """tests/test_image_storage.py::SupabaseBackendTest::test_delete_targets_the_object_behind_the_public_url"""
        with patch("common.storage.supabase.requests.delete") as request_delete:
            request_delete.return_value = Mock(ok=True)
            delete_image(PUBLIC_PREFIX + "products/a.png")
        self.assertEqual(
            request_delete.call_args.args[0],
            "https://sb.example/storage/v1/object/product-images/products/a.png",
        )
        self.assertEqual(
            request_delete.call_args.kwargs["headers"]["apikey"], "sb_secret_test"
        )

    def test_a_failing_delete_is_swallowed(self):
        """tests/test_image_storage.py::SupabaseBackendTest::test_a_failing_delete_is_swallowed"""
        with patch("common.storage.supabase.requests.delete") as request_delete:
            request_delete.return_value = Mock(ok=False, status_code=404, text="missing")
            delete_image(PUBLIC_PREFIX + "products/a.png")  # must not raise

    def test_a_url_from_neither_backend_is_left_alone(self):
        """tests/test_image_storage.py::SupabaseBackendTest::test_a_url_from_neither_backend_is_left_alone"""
        with patch("common.storage.supabase.requests.delete") as request_delete:
            delete_image("https://cdn.example/somebody-elses/a.png")
            delete_image("")
        request_delete.assert_not_called()

    def test_a_local_url_is_still_deleted_from_disk_after_switching_backend(self):
        """tests/test_image_storage.py::SupabaseBackendTest::test_a_local_url_is_still_deleted_from_disk_after_switching_backend"""
        # An image uploaded before the bucket existed must still be cleanable.
        with override_settings(**SUPABASE_UNCONFIGURED):
            url = upload_image(_image(), folder="products")
        self.assertTrue(_path_of(url).is_file())

        delete_image(url)
        self.assertFalse(_path_of(url).exists())


@override_settings(**SUPABASE_UNCONFIGURED)
class ImageValidationTest(SimpleTestCase):
    """Limits that apply identically on both backends.

    tests/test_image_storage.py::ImageValidationTest
    """

    def test_unsupported_content_type_is_rejected(self):
        """tests/test_image_storage.py::ImageValidationTest::test_unsupported_content_type_is_rejected"""
        with pytest.raises(serializers.ValidationError, match="JPEG, PNG or WebP"):
            upload_image(_image(content_type="application/pdf"), folder="products")
        self.assertFalse(Path(settings.MEDIA_ROOT).exists())

    def test_oversized_image_is_rejected(self):
        """tests/test_image_storage.py::ImageValidationTest::test_oversized_image_is_rejected"""
        oversized = _image(content=b"x" * (MAX_IMAGE_BYTES + 1))
        with pytest.raises(serializers.ValidationError, match="5 MB or smaller"):
            upload_image(oversized, folder="products")
        self.assertFalse(Path(settings.MEDIA_ROOT).exists())
