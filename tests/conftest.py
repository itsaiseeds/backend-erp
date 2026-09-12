"""Shared pytest fixtures for the Django test suite."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.db import connection
from django.test import override_settings

DML_PATH = Path(__file__).resolve().parents[1] / "sql" / "dml.sql"


def load_dml(cursor) -> None:
    """Replace the migration-generated reference data with ``dml.sql``'s.

    Django's ``post_migrate`` signal already populated ``django_content_type``
    and ``auth_permission`` with auto-assigned ids when the test database was
    built. ``dml.sql`` re-seeds both with the canonical production ids, so the
    migration-generated rows are dropped first to avoid primary-key collisions
    (``auth_permission`` before ``django_content_type``, to respect the FK).
    ``dml.sql`` re-syncs the seeded tables' sequences itself, so rows created
    later by test fixtures get ids after the seeded maximum.
    """
    dml = DML_PATH.read_text(encoding="utf-8")
    # The caller owns the transaction, so do not nest dml.sql's own BEGIN/COMMIT.
    dml = re.sub(r"(?m)^(BEGIN|COMMIT);\s*$", "", dml)
    cursor.execute("DELETE FROM auth_permission; DELETE FROM django_content_type;")
    cursor.execute(dml)


def pytest_collection_modifyitems(items):
    """Tag every test ``unit`` or ``dml`` according to what it actually needs.

    The split is derived from the base class rather than declared per file, so
    it cannot drift: anything deriving from :class:`tests.common.DMLTestCase`
    touches the seeded database and is ``dml``; everything else (a
    ``SimpleTestCase`` or a bare pytest function) needs no database and is
    ``unit``. ``bash scripts/run.sh test-unit`` / ``test-dml`` select on these.
    """
    from tests.common import DMLTestCase

    for item in items:
        owner = getattr(item, "cls", None)
        needs_db = owner is not None and issubclass(owner, DMLTestCase)
        item.add_marker("dml" if needs_db else "unit")


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):  # noqa: PT004
    """Seed the DML baseline into the test database once per session.

    Every DB-backed test case in this suite derives from
    :class:`tests.common.DMLTestCase`, which is a Django ``TestCase``: each test
    *and* each class's ``setUpTestData`` runs inside a transaction that is
    rolled back afterwards, so nothing a test writes can ever reach this
    baseline. Loading it once here instead of once per test class removes one
    ~0.5s SQL replay per class, and under ``pytest-xdist`` it runs once per
    worker database.
    """
    with django_db_blocker.unblock(), connection.cursor() as cursor:
        # ``--reuse-db`` hands back a database that already holds the baseline,
        # and dml.sql's INSERTs carry explicit ids with no ON CONFLICT clause,
        # so re-running it there would fail on duplicate keys.
        cursor.execute("SELECT 1 FROM authentication_user WHERE phone_number = '9999999999'")
        if cursor.fetchone() is None:
            load_dml(cursor)
    yield


@pytest.fixture(autouse=True)
def isolated_media_root(tmp_path):
    """Point ``MEDIA_ROOT`` at a per-test temp directory.

    Tests exercise the real on-disk image backend (Supabase is unconfigured in
    CI, so ``common.storage`` selects local disk). Without this, uploads would
    write into the repo's own ``media/`` and leak between tests.
    """
    with override_settings(MEDIA_ROOT=str(tmp_path / "media")):
        yield
