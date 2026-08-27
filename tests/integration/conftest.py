"""Session-scoped fixtures for the live-server integration tests.

The heavy lifting lives in :mod:`tests.integration.base` as classes
(``IntegrationDbContext`` and ``LiveServer``); this module only wires them into
pytest fixtures.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from requests import Session

from tests.integration.base import IntegrationDbContext, LiveServer


@pytest.fixture(scope="session")
def db_context() -> IntegrationDbContext:
    """A configured manager for the dedicated integration-test database."""
    context = IntegrationDbContext()
    context.build()
    context.mark_migrations_applied()
    return context


@pytest.fixture(scope="session")
def api_base_url(db_context: IntegrationDbContext) -> Iterator[str]:
    """Yield the base URL of a live Django server pointed at the test DB."""
    with LiveServer(db_context) as server:
        yield server.base_url


@pytest.fixture(scope="session")
def client() -> Session:
    """A ``requests.Session`` (cookies persist, so logins carry across tests)."""
    return Session()
