"""Shared test-case base classes."""

from __future__ import annotations

import re
from pathlib import Path

from django.db import connection
from django.test import TestCase


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
            cursor.execute(dml)
