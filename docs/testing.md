# Testing conventions

> How this suite is organised and, more importantly, what it deliberately does
> **not** test twice. Read this before adding a test file.
>
> See also: [`.agents/skills/run-tests/SKILL.md`](../.agents/skills/run-tests/SKILL.md)
> for the commands, [`skills/conventions.md`](../skills/conventions.md) for the
> DRY/YAGNI/KISS principles these rules apply to tests.

---

## 1. The one rule: a shared behaviour is tested where it is implemented

The single largest source of waste in a test suite is re-proving inherited
behaviour once per subclass. Every endpoint in this project inherits *all* of
its authentication and role gating from a base class:

```
BaseApiView            (api/views.py)          -- flags -> permission classes
├── AdminApiView       (api/admin.py)          -- session cookie only
└── AndroidBaseView    (android/api/base.py)   -- bearer token, salesperson_required
```

A concrete view never re-implements that logic; it only *declares* flags
(`admin_required`, `superuser_required`, `salesperson_required`). Therefore:

> **Do not write per-endpoint authentication tests.**
> No `test_anonymous_requests_are_rejected`, no `test_non_admin_rejected`, no
> `test_session_login_does_not_authenticate`, on any endpoint module.

Those belong to `tests/test_view_contracts.py`, which owns the whole contract in
three layers:

| Layer | Class | What it proves |
|---|---|---|
| Unit | `BaseApiViewFlagTest` | Each flag combination maps to the right DRF permission classes, and each base fixes one credential scheme. |
| Registry | `ViewContractRegistryTest` | Every routed view declares the contract it is supposed to, checked against an explicit table; no view hand-rolls `permission_classes`; only the two login endpoints bypass `BaseApiView`. |
| End to end | `SessionAuthContractTest`, `TokenAuthContractTest` | One real HTTP round trip per credential scheme and role flag: anonymous → 401, wrong role → 403, right role → 200, wrong scheme → 401. |

The registry layer is what makes deleting the per-endpoint tests *safe*, and
strictly stronger than what they gave us: a copy-pasted 403 test only covered
the endpoint someone remembered to write it for, while the table covers every
routed view — including ones with no test file at all.

### When you add an endpoint

Add its path to `EXPECTED_CONTRACTS` in `tests/test_view_contracts.py`. The
suite fails until you do; that failure is the review prompt for "who may call
this?". Then test only what the endpoint *does*.

### The line between a view flag and a domain rule

Test it in the endpoint module, not the contracts file, when the check is **not**
a `BaseApiView` flag. Examples that stay local:

- `can_update_stock_count` on `Admin` — a column, checked inside the operations
  layer (`tests/test_inventory_api.py`, `tests/test_loose_stock_api.py`).
- Row scoping: a sales person seeing only their own clients, which is a
  queryset filter producing 404, not 403 (`tests/android/test_clients.py`).
- Model-level actor validation: `verify_client` refusing a non-admin
  (`tests/test_client_model.py`).

Rule of thumb: if the answer is 401 or 403 and comes from a class flag, it is
the contracts file's job. If it is 400 or 404, or comes from a column or a
queryset, it is the endpoint's job.

---

## 2. Combine tests that share a request

Two tests that issue the same request and assert on different fields of the same
response are one test. The HTTP round trip, not the assertion, is what costs
time. Prefer:

```python
def test_post_update_inventory_replaces_the_whole_day(self):
    resp = self._stock_admin_request("post", UPDATE_URL, data=..., format="json")
    # ...assert the list length, the counted row's shape, the zero-filled row,
    #    and that the day now reads as complete -- all from this one response.
```

over four tests that each re-POST and check one field.

## 3. Use a `subTest` table for a family of cases

When cases differ only in input and expected outcome, write one test with a
table and `self.subTest`. Every case still reports its own pass/fail, and the
fixture is built once:

```python
def test_invalid_crop_names_are_rejected_on_create_and_update(self):
    cases = [
        ("empty", {"name": ""}),
        ("whitespace only", {"name": "   "}),
        ("missing", {}),
        ("duplicate", {"name": "Wheat"}),
    ]
    for label, body in cases:
        with self.subTest(verb="POST", case=label):
            ...
```

Label every case — an unlabelled `subTest` failure is hard to read. Keep a case
out of the table when it needs materially different setup; a table whose body is
full of `if label == ...` branches is two tests wearing one hat.

## 4. One class per fixture, not one class per endpoint

Every DB-backed class pays for its own `setUpTestData`. Endpoints that need the
same fixture share a class:

- `tests/test_auth_flow.py` — the whole web session lifecycle (login, what the
  session identifies, expiry, logout).
- `tests/android/test_authenticated_endpoints.py` — reauthenticate, logout and
  the city picker, which all need one sales person and one token.
- `tests/test_geography_utilities.py` — countries, states and cities.

Split only when the fixtures genuinely diverge (e.g. `tests/android/test_login.py`
needs TOTP enrolment and a per-test throttle reset).

## 5. Every test states its node id

Every test class and method carries a docstring containing its exact pytest node
id (`tests/<file>.py::<Class>::<method>`), to paste straight into a terminal.
This is a hard convention — see the `run-tests` skill.

---

## 6. Test isolation: what is reset, and where

`tests/common.py::DMLTestCase` is the base for every DB-backed test. Isolation
comes from three layers, because Postgres rolls back only the first of them.

### Rows -- rolled back by the transaction

`DMLTestCase` is a Django `TestCase`, so each class's `setUpTestData` and each
test method run inside nested transactions that are rolled back afterwards.
Rows written by a test never reach the next one, and never reach the DML
baseline -- which is why `sql/dml.sql` can be loaded once per test *database*
(the session-scoped `django_db_setup` fixture in `tests/conftest.py`) instead of
once per class.

Query the seeded rows instead of recreating them: the superuser on phone
`9999999999`, the India / Gujarat / Surat / Ahmedabad geography, the `Status`
and `Stage` rows.

> Do **not** introduce a `TransactionTestCase` here without revisiting that
> fixture; those commit, and would corrupt the shared baseline. `SimpleTestCase`
> (no database at all) is fine, and is the right base for pure unit tests like
> `tests/test_paginated_filters.py`.

### Primary keys -- rewound explicitly

Postgres sequences are deliberately **non-transactional**: `nextval` is never
rolled back. So a row created by a rolled-back test still burns its id, and the
next test's rows come out with different primary keys -- 4, 5, 6 in the first
test, then 7, 8, 9 in the second, and so on.

Ids are part of the state a test observes, so that drift makes the suite
order-dependent. It is not hypothetical: `test_admin_create_crop_payload_shape...`
asserts the new crop takes the id after the seeded one, and that assertion held
only because the test happened to sort first alphabetically. Reversing the
collection order made it fail.

`DMLTestCase` therefore snapshots every sequence in `setUpClass` -- after
`setUpTestData` has run, so the baseline includes the class fixtures -- and
rewinds all 35 of them in `setUp`, in one round trip:

```sql
SELECT setval(s.name::regclass, s.value, s.is_called)
  FROM unnest(%s::text[], %s::bigint[], %s::boolean[]) AS s(name, value, is_called)
```

`setval` is itself non-transactional, so the rewind survives the rollback at the
end of the test. Every test method genuinely starts from the same ids, which
makes an assertion like `crop["id"] == self.crop.id + 1` sound rather than
lucky. Cost is roughly 1 ms per test.

### Caches and files -- cleared per test

- `DMLTestCase.setUp` calls `cache.clear()`. Throttle counters live in Django's
  `LocMemCache`, which no transaction rolls back; without this one test's
  requests count against the next test's per-IP budget on the shared
  `127.0.0.1` origin. Do not re-add a local `cache.clear()` to a test class.
- The autouse `isolated_media_root` fixture points `MEDIA_ROOT` at a per-test
  `tmp_path`, so uploads never leak between tests or into the repo's `media/`.

### If you add state that lives outside the transaction

Reset it in `DMLTestCase.setUp` alongside the sequences and the cache -- not in
the individual test class. Anything else (a real external service, a fixed
port, a file at a hard-coded path) will be flaky under xdist too; make the
dependency per-test rather than serialising the suite.

---

## 7. Running tests in parallel

The suite runs on `pytest-xdist`. `bash scripts/run.sh test` is parallel by
default:

```bash
bash scripts/run.sh test                  # everything, 4 workers (~23s)
bash scripts/run.sh test-unit             # no-database tests only (~8s)
bash scripts/run.sh test-dml              # database tests only (~23s)
bash scripts/run.sh test-serial           # everything, one worker, verbose
bash scripts/run.sh test-serial tests/test_view_contracts.py::BaseApiViewFlagTest
TEST_WORKERS=8 bash scripts/run.sh test   # override the worker count
```

The `unit` / `dml` split is not declared per file. `tests/conftest.py`'s
`pytest_collection_modifyitems` derives it from each test's base class --
`DMLTestCase` subclass means `dml`, anything else means `unit` -- so it cannot
drift as tests are added. Never add these markers by hand.

Two flags matter and both are already set by `run.sh`:

- **`-n 4`.** Four is the measured sweet spot on a 16-core machine. Each worker
  creates and migrates its own test database and loads the DML baseline into it,
  so past four workers that per-worker setup costs more than the extra
  parallelism saves (measured: 4 workers 23s, 8 workers 25s, 16 workers 31s).
- **`--dist loadscope`.** Groups tests by class so a class's `setUpTestData`
  runs once, on one worker, instead of once per worker that happens to receive
  one of its methods. Without it, expensive class fixtures are rebuilt several
  times over.

### What makes this suite safe to parallelise

Everything in section 6 is per-worker as well as per-test: `pytest-django`
gives each xdist worker its own database (`test_<name>_gw0`, `_gw1`, …) with
its own sequences, `LocMemCache` is per-process, and `tmp_path` is per-worker.
So workers cannot share rows, burn each other's ids, or exhaust each other's
rate-limit budget.

`--reuse-db` is supported: the DML fixture checks for the seeded superuser
before loading, since `dml.sql` writes explicit ids with no `ON CONFLICT`
clause and would otherwise fail on a second load.
