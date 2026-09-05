"""Shared test-case base classes."""

from __future__ import annotations

import re
from pathlib import Path

from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient


class DMLTestCase(TestCase):
    """A Django test case seeded from the project's canonical ``dml.sql`` data.

    ``TestCase`` wraps the class fixtures and each test in nested transactions.
    The DML baseline and subclass ``setUpTestData`` records are therefore
    available to every test method, while records created or changed by an
    individual test are rolled back before the next method runs.
    """

    @classmethod
    def setUpTestData(cls):
        """Load the DML baseline before subclasses create their own fixtures."""
        super().setUpTestData()
        dml_path = Path(__file__).resolve().parents[1] / "sql" / "dml.sql"
        dml = dml_path.read_text(encoding="utf-8")
        # ``TestCase`` already owns the transaction, so do not nest dml.sql's
        # standalone transaction statements inside it.
        dml = re.sub(r"(?m)^(BEGIN|COMMIT);\s*$", "", dml)
        with connection.cursor() as cursor:
            # Django's post_migrate signal already populated
            # django_content_type and auth_permission with auto-assigned ids
            # when the test database was built. dml.sql re-seeds both with the
            # canonical production ids, so drop the migration-generated rows
            # first to avoid primary-key collisions. auth_permission is deleted
            # before django_content_type to respect the FK.
            cursor.execute(
                "DELETE FROM auth_permission; DELETE FROM django_content_type;"
            )
            # dml.sql re-syncs the seeded tables' sequences itself, so ORM rows
            # created by subclass fixtures get ids after the seeded maximum.
            cursor.execute(dml)


class WebApiTestCase(DMLTestCase):
    """Base for session-only web (sales-admin) endpoint tests.

    Provides an unauthenticated :class:`APIClient` per test and the one
    credential mechanism the web side ever uses -- a logged-in browser
    session -- so individual test modules don't hand-roll their own
    ``_auth_as`` / ``_clear_auth`` helpers around ``force_login``. See
    ``tests.android.common.AndroidApiTestCase`` for the token-based
    counterpart.
    """

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def login_as(self, user) -> None:
        """Authenticate ``self.client`` as ``user`` via a browser session."""
        self.client.force_login(user)

    def clear_auth(self) -> None:
        """Drop the current session, leaving the client anonymous."""
        self.client.logout()
