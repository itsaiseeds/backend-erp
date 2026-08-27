---
name: run-tests
description: How to run backend-erp tests (pytest) inside the Docker web container — everything, only unit, all integration, one class, or a single test — plus the mandatory convention that every test's docstring contains its copy/paste pytest node id. Use when the user asks how to run tests, how to run one test or class, mentions test-integration, pytest, django_test, AuthFlowTest, or when writing/fixing a test file that needs its runnable node id.
---

# Running tests (backend-erp)

All tests run **inside the `web` Docker container** via `scripts/run.sh`. The
host Python (e.g. VS Code's debugpy / host interpreter) does NOT have Django or
the project deps, so never run pytest on the host.

Prerequisites:

- `docker compose up -d` (db + web up). Check: `bash scripts/run.sh status`.
- After changing `requirements.txt`, rebuild the image first:
  `bash scripts/run.sh build` (the running container is NOT updated in place).

## Commands (from the repo root, in Git Bash)

| What you want                          | Command                                                              |
| -------------------------------------- | -------------------------------------------------------------------- |
| Everything (unit + integration)        | `bash scripts/run.sh test`                                            |
| Unit tests only                        | `bash scripts/run.sh test-unit`                                       |
| All integration tests                  | `bash scripts/run.sh test-integration`                                |
| One test CLASS                         | `bash scripts/run.sh test-integration tests/integration/test_auth_flow.py::AuthFlowTest` |
| One test METHOD                        | `bash scripts/run.sh test-integration tests/integration/test_auth_flow.py::AuthFlowTest::test_generate_otp_returns_200` |
| Several tests at once                  | `bash scripts/run.sh test-integration "tests/a.py::C::t1 tests/a.py::C::t2"` |
| Lint / typecheck                       | `bash scripts/run.sh lint` / `bash scripts/run.sh typecheck`           |

Any extra `pytest` args can be appended after the node id, e.g.
`bash scripts/run.sh test-integration tests/integration -k otp`.

## From the VS Code UI

Terminal > Run Task... (Ctrl+Shift+R on Windows):

- `test` — full suite.
- `test: unit` — unit only.
- `test-integration: all tests` — whole integration suite.
- `test-integration: pick a test` — **asks for a pytest node id**, then runs it.

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