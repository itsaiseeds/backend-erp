"""Shared test-case base classes."""

from __future__ import annotations

from typing import ClassVar

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

# Every sequence in the schema, with the value to rewind it to. ``last_value``
# is NULL until a sequence has been used, which is why ``start_value`` and the
# is_called flag are read alongside it -- setval() needs both to reproduce an
# untouched sequence exactly.
_SNAPSHOT_SEQUENCES = """
    SELECT quote_ident(schemaname) || '.' || quote_ident(sequencename),
           coalesce(last_value, start_value),
           last_value IS NOT NULL
      FROM pg_sequences
     WHERE schemaname = 'public'
"""

# Rewind all 35 sequences in one round trip. The three snapshot columns go in
# as arrays rather than being spliced into the statement, so there is no
# dynamically built SQL here.
_RESTORE_SEQUENCES = """
    SELECT setval(s.name::regclass, s.value, s.is_called)
      FROM unnest(%s::text[], %s::bigint[], %s::boolean[])
        AS s(name, value, is_called)
"""


class DMLTestCase(TestCase):
    """A Django test case seeded from the project's canonical ``dml.sql`` data.

    The DML baseline is loaded once per test *database* by the session-scoped
    ``django_db_setup`` fixture in ``tests/conftest.py``, not once per class:
    ``TestCase`` wraps every class's ``setUpTestData`` and every test method in
    nested transactions that are rolled back, so no test can disturb it. The
    baseline and the subclass's own ``setUpTestData`` records are therefore
    available to every test method, while records created or changed by an
    individual test are rolled back before the next method runs.

    Subclasses that need the seeded rows can simply query them (e.g. the
    superuser on phone ``9999999999``, or the India/Gujarat/Surat geography).

    Two pieces of state live *outside* that transaction and are reset here
    instead, so that a test sees the same starting point no matter what ran
    before it -- see :meth:`setUp`.
    """

    # Three parallel columns -- sequence name, value, is_called -- captured in
    # setUpClass and replayed in setUp. See _restore_sequences.
    _sequence_baseline: ClassVar[list[list[str] | list[int] | list[bool]]] = []

    @classmethod
    def setUpClass(cls):
        """Record the sequence positions left by this class's ``setUpTestData``.

        ``TestCase.setUpClass`` opens the class-level atomic block and runs
        ``setUpTestData`` inside it, so by the time ``super()`` returns every
        class fixture row exists and the sequences have advanced past them.
        That -- not the bare DML baseline -- is the position each test method
        must start from.
        """
        super().setUpClass()
        with connection.cursor() as cursor:
            cursor.execute(_SNAPSHOT_SEQUENCES)
            rows = cursor.fetchall()
        # Kept column-wise so the rewind can pass three arrays to one statement.
        cls._sequence_baseline = [list(column) for column in zip(*rows, strict=True)]

    def setUp(self):
        """Rewind the non-transactional state a previous test may have moved."""
        super().setUp()
        self._restore_sequences()
        # Throttle counters live in Django's LocMemCache, which no transaction
        # rolls back: without this, one test's requests count against the next
        # test's per-IP budget on the shared 127.0.0.1 origin.
        cache.clear()

    def _restore_sequences(self) -> None:
        """Rewind every sequence to the position captured in ``setUpClass``.

        Postgres sequences are deliberately non-transactional: ``nextval`` is
        never rolled back, so without this a row created by a rolled-back test
        still burns its id and the *next* test's rows come out with different
        primary keys. Ids are part of the state a test observes, so leaving
        them to drift makes the suite order-dependent -- an assertion like
        "the created crop got the next id after the seeded one" would hold or
        fail depending on which tests ran first.

        ``setval`` is itself non-transactional, so this rewind survives the
        rollback at the end of the test and each test method genuinely begins
        from the same ids.
        """
        if not self._sequence_baseline:
            return
        with connection.cursor() as cursor:
            cursor.execute(_RESTORE_SEQUENCES, self._sequence_baseline)


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
