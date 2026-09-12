---
name: run-tests
description: How to run backend-erp tests (pytest) inside the Docker web container — everything (in parallel, via pytest-xdist), serially, all integration, one class, or a single test — plus the mandatory convention that every test's docstring contains its copy/paste pytest node id. Use when the user asks how to run tests, how to run one test or class, mentions test-integration, pytest, django_test, AuthFlowTest, or when writing/fixing a test file that needs its runnable node id.
---

# Running tests (backend-erp)

All tests run **inside the `web` Python image** via `scripts/run.sh`, in
short-lived one-off containers (the running `web` service/gunicorn is NOT used
for tests). The host Python (e.g. VS Code's debugpy / host interpreter) does NOT
have Django or the project deps, so never run pytest on the host.

Prerequisites:

- The `db` service must be up: `docker compose up -d db`. Check:
  `bash scripts/run.sh status`.
- After changing `requirements.txt`, rebuild the image first:
  `bash scripts/run.sh build` (the running container is NOT updated in place).

## Commands (from the repo root, in Git Bash)

| What you want                          | Command                                                              |
| -------------------------------------- | -------------------------------------------------------------------- |
| Everything, in parallel (the default)  | `bash scripts/run.sh test`                                            |
| Everything, one worker (clearer output)| `bash scripts/run.sh test-serial`                                     |
| No-database tests only (fast, ~8s)     | `bash scripts/run.sh test-unit`                                       |
| DML-seeded database tests only         | `bash scripts/run.sh test-dml`                                        |
| All integration tests                  | `bash scripts/run.sh test-integration`                                |
| One test class                         | `bash scripts/run.sh test-serial tests/test_crop_api.py::CropApiTest`  |
| One test                               | `bash scripts/run.sh test-serial tests/test_crop_api.py::CropApiTest::test_admin_update_crop` |
| One integration test class             | `bash scripts/run.sh test-integration tests/integration/test_sentry_probe.py::SentryProbeTest` |
| Several tests at once                  | `bash scripts/run.sh test-integration "tests/a.py::C::t1 tests/a.py::C::t2"` |
| Lint / typecheck                       | `bash scripts/run.sh lint` / `bash scripts/run.sh typecheck`           |

Any extra `pytest` args can be appended after the node id, e.g.
`bash scripts/run.sh test-serial tests/ -k otp`.

## Parallel execution

`test`, `test-unit` and `test-dml` run on `pytest-xdist` with `-n 4
--dist loadscope`. Override the worker count with `TEST_WORKERS`:

```bash
TEST_WORKERS=8 bash scripts/run.sh test
```

Four is the measured sweet spot on a 16-core machine — each worker builds its
own test database, so more workers eventually cost more in setup than they save.
`test-unit` / `test-dml` select on markers that `tests/conftest.py` applies
automatically from each test's base class (`DMLTestCase` => `dml`, anything
else => `unit`); never add those markers by hand.
`--dist loadscope` keeps a test class on one worker so its `setUpTestData` runs
once. Use `test-serial` when you are reading a failure: xdist interleaves
output from every worker.

Full rationale and the parallel-safety rules for new tests:
[`docs/testing.md`](../../../docs/testing.md).

## Before adding a test: what NOT to write

**Never add a per-endpoint authentication test** — no
`test_anonymous_requests_are_rejected`, `test_non_admin_rejected`, or
`test_session_login_does_not_authenticate` on any endpoint module. Every view
inherits its credential scheme and role gating from `AdminApiView` or
`AndroidBaseView`, and that contract is owned once by
`tests/test_view_contracts.py`.

When you add an endpoint, add its path to `EXPECTED_CONTRACTS` there — the
suite fails until you do — then test only what the endpoint *does*. See
[`docs/testing.md`](../../../docs/testing.md) for the full rule, including where
the line falls between a view flag (contracts file) and a domain rule such as
`can_update_stock_count` or row scoping (the endpoint's own module).

## From the VS Code UI

Terminal > Run Task... (Ctrl+Shift+R on Windows):

- `test` — whole suite, in parallel (the default test task).
- `test: no-database only (fast)` — the `unit`-marked tests.
- `test: database only` — the `dml`-marked tests.
- `test: pick a test` — **asks for a pytest node id**, then runs it serially.
- `test: serial (readable failures)` — whole suite, one worker, verbose.

There is no launch.json (debug attach) in this project; tasks are the way to
run tests.

## What running an integration test does

For each `test-integration` run, `tests/integration/conftest.py`:

1. Drops + recreates the `django_test` Postgres DB from `sql/ddl.sql` and
   `sql/dml.sql` (seeded superuser phone `9999999999`).
2. Runs `manage.py migrate --fake` so the live server uses the pre-built
   schema.
3. Starts a real Django dev server on `127.0.0.1:8001` inside the container.
4. Your tests hit that server over HTTP (`tests/integration/base.py`
   `IntegrationTestCase` provides `self.client` + `self.get/post/put/patch/delete`).

## Convention: every test must state its runnable node id (REQUIRED)

Every test class and every test method **must** have a docstring that contains
the exact pytest node id (`tests/<file>.py::<Class>::<method>`) to paste into a
terminal or the "pick a test" task prompt.

- Keep the docstring to the node id alone (no `python -m pytest ... -v`
  wrapper) so lines stay under 100 chars and ruff stays clean.
- No trailing whitespace.

Example (`tests/integration/test_auth_flow.py`):

```python
class AuthFlowTest(IntegrationTestCase):
    """Covers the OTP request + verify endpoints of the sales admin API.
    Run: tests/integration/test_auth_flow.py::AuthFlowTest
    """

    def test_generate_otp_returns_200(self):
        """Run: tests/integration/test_auth_flow.py::AuthFlowTest::test_generate_otp_returns_200"""
        ...
```

- To list every available node id: `docker compose exec -T web python -m pytest tests/integration --collect-only -q`.
- Node id = `/path/relative/to/repo/test_file.py::ClassName::test_name`. Class
  names end in `Test` (e.g. `AuthFlowTest`); pytest is configured to collect
  both `Test*` and `*Test` classes (`python_classes` in `pyproject.toml`).
