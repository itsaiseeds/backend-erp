"""Shared pytest fixtures for the Django test suite."""

from __future__ import annotations

import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def isolated_media_root(tmp_path):
    """Point ``MEDIA_ROOT`` at a per-test temp directory.

    Tests exercise the real on-disk image backend (Supabase is unconfigured in
    CI, so ``common.storage`` selects local disk). Without this, uploads would
    write into the repo's own ``media/`` and leak between tests.
    """
    with override_settings(MEDIA_ROOT=str(tmp_path / "media")):
        yield
