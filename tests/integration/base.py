"""Class-based infrastructure for the live-server integration tests.

Everything here is *container-native*: it talks to Postgres through psycopg
directly (no shelling out to host docker) so the same code runs whether pytest
runs inside the ``web`` container or on a host that can reach Postgres.

* :class:`IntegrationDbContext` - builds/checks/drops the Postgres test DB
  from ``sql/ddl.sql`` + ``sql/dml.sql``.
* :class:`LiveServer`          - starts/stops/wait-for the real Django server.
* :class:`IntegrationTestCase` - base test class; subclasses inherit
  ``self.client`` and ``self.base_url`` plus HTTP helpers.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import psycopg
import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # backend-erp
INTEGRATION_DB = "django_test"
INTEGRATION_PORT = 8001
HOST = "127.0.0.1"
BASE_URL = f"http://{HOST}:{INTEGRATION_PORT}"

# Tolerances for async startup of db + server.
DB_TIMEOUT_SECONDS = 120
SERVER_TIMEOUT_SECONDS = 60

ADMIN_DB = "postgres"  # maintenance DB used to CREATE/DROP test databases.
SQL_DIR = REPO_ROOT / "sql"


def _db_host() -> str:
    """Postgres host to connect to.

    Defaults to ``db`` (the Docker service name) since tests are expected to
    run inside the ``web`` container on the same Docker network. Override with
    the ``TEST_DB_HOST`` environment variable to run on a host instead.
    """
    return os.environ.get("TEST_DB_HOST", "db")


class IntegrationDbContext:
    """Manage the dedicated Postgres test database (DDL + DML)."""

    def __init__(self, db_name: str = INTEGRATION_DB) -> None:
        self.db_name = db_name
        self.host = _db_host()
        self.port = os.environ.get("POSTGRES_PORT", "5432")
        self.user = os.environ.get("POSTGRES_USER", "django")
        self.password = os.environ.get("POSTGRES_PASSWORD", "")

    # -- psycopg helpers -------------------------------------------------------
    def _connect(self, db: str):
        """Open a psycopg[3] connection (autocommit so DDL works outside txn)."""
        return psycopg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=db,
            autocommit=True,
        )

    def _execute(self, db: str, sql: str) -> None:
        with self._connect(db) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def _run_sql_file(self, db: str, file: Path) -> None:
        with self._connect(db) as conn:
            # ddl.sql/dml.sql contain multi-statement scripts + BEGIN/COMMIT.
            conn.execute(file.read_text())

    # -- Django env for subprocesses (runserver, migrate) ----------------------
    def django_env(self) -> dict[str, str]:
        """Environment for Django subprocesses pointed at this test DB."""
        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = "config.settings"
        env["POSTGRES_DB"] = self.db_name
        env["POSTGRES_HOST"] = self.host
        env["POSTGRES_PORT"] = self.port
        env["POSTGRES_USER"] = self.user
        env["POSTGRES_PASSWORD"] = self.password
        env["DEBUG"] = "False"
        env["SECRET_KEY"] = env.get("SECRET_KEY", "integration-test-secret")
        env["ALLOWED_HOSTS"] = f"{HOST},127.0.0.1,localhost"
        return env

    # -- Lifecycle -------------------------------------------------------------
    def build(self) -> None:
        """Drop any existing test DB, then (re)create it from DDL + DML."""
        self.drop()
        self._execute(
            ADMIN_DB,
            f'CREATE DATABASE "{self.db_name}" OWNER "{self.user}";',
        )
        self._run_sql_file(self.db_name, SQL_DIR / "ddl.sql")
        self._run_sql_file(self.db_name, SQL_DIR / "dml.sql")

    def wait_until_ready(self, timeout: int = DB_TIMEOUT_SECONDS) -> None:
        """Poll until the database accepts Django connections."""
        env = self.django_env()
        deadline = time.time() + timeout
        while time.time() < deadline:
            proc = subprocess.run(
                [sys.executable, "manage.py", "showmigrations", "--plan"],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                return
            time.sleep(2)
        raise RuntimeError("Test database never became reachable.")

    def mark_migrations_applied(self) -> None:
        """``migrate --fake`` so runserver runs against the pre-built DDL schema."""
        self.wait_until_ready()
        proc = subprocess.run(
            [sys.executable, "manage.py", "migrate", "--fake"],
            cwd=REPO_ROOT,
            env=self.django_env(),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"manage.py migrate --fake failed.\n"
                f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

    def drop(self) -> None:
        """Drop the test database, ignoring errors if it is already gone."""
        try:
            self._execute(
                ADMIN_DB,
                f'DROP DATABASE IF EXISTS "{self.db_name}" WITH (FORCE);',
            )
        except psycopg.Error:
            pass


class LiveServer:
    """Manage a real Django dev server for the duration of a test session."""

    def __init__(
        self,
        db_context: IntegrationDbContext,
        host: str = HOST,
        port: int = INTEGRATION_PORT,
    ) -> None:
        self.db_context = db_context
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._proc: subprocess.Popen | None = None

    def _wait_until_serving(self, timeout: int = SERVER_TIMEOUT_SECONDS) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                # base_url is built from module constants, never from user input.
                urllib.request.urlopen(f"{self.base_url}/api/schema/", timeout=3)  # noqa: S310
                return
            except urllib.error.HTTPError:
                # Any HTTP response (even 400/403) means the server accepts
                # request, which is all we need to probe for here.
                return
            except Exception:
                time.sleep(1)
        raise RuntimeError(f"Integration server did not start on {self.base_url}")

    # -- Context manager ---------------------------------------------------------
    def __enter__(self) -> LiveServer:
        if self._proc is not None:
            raise RuntimeError("LiveServer already running")
        self._proc = subprocess.Popen(  # noqa: S603  (fixed args + sys.executable)
            [
                sys.executable,
                "manage.py",
                "runserver",
                f"{self.host}:{self.port}",
                "--noreload",
            ],
            cwd=REPO_ROOT,
            env=self.db_context.django_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            self._wait_until_serving()
        except Exception:
            self.stop()
            raise
        return self

    def __exit__(self, *exc_info) -> None:
        self.stop()

    def stop(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None


class IntegrationTestCase:
    """Base class for endpoint integration tests.

    Subclasses get ``self.client`` (a ``requests.Session`` with cookies, so
    session login persists across tests in the same run) and ``self.base_url``
    automatically, courtesy of the autouse fixtures below.
    """

    base_url: str

    @pytest.fixture(autouse=True)
    def _inject_client(self, client: requests.Session) -> None:
        """Bind the shared HTTP session so tests can call ``self.client``."""
        self.client = client

    @pytest.fixture(autouse=True)
    def _inject_base_url(self, api_base_url: str) -> None:
        """Bind the live server base URL so tests can call ``self.base_url``."""
        self.base_url = api_base_url

    # -- HTTP helpers -------------------------------------------------------------
    def get(self, path: str, **kwargs) -> requests.Response:
        return self.client.get(f"{self.base_url}{path}", **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.client.post(f"{self.base_url}{path}", **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.client.put(f"{self.base_url}{path}", **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self.client.patch(f"{self.base_url}{path}", **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.client.delete(f"{self.base_url}{path}", **kwargs)
