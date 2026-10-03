"""Run low-priority work off the request thread, after the transaction commits."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from django.db import connections, transaction

logger = logging.getLogger(__name__)


def fire_and_forget(func: Callable[[], object]) -> None:
    """Run ``func`` in a background thread after the current transaction commits.

    Use this for low-priority, "nice to have" work that must never fail the API
    response (audit logs, notifications, cache warming, ...). ``func`` runs
    exactly once the surrounding transaction has committed, in a daemon thread,
    and any exception it raises is logged and never propagated to the caller.
    The thread's own database connections are closed when it finishes.
    """

    def run() -> None:
        try:
            func()
        except Exception:
            logger.exception("Background task failed.")
        finally:
            connections.close_all()

    thread = threading.Thread(target=run, daemon=True, name="fire-and-forget")
    transaction.on_commit(thread.start)
