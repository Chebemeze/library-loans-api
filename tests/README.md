# Tests: the Library Loans API release harness

Owner: **Member 2**. Everything here is black-box: the tests speak HTTP to the
ASGI app and read the database directly, but never import routers, services or
repositories. That way a refactor that keeps the contract keeps the tests green.

## Run

```bash
uv run pytest                     # whole suite
uv run pytest tests/test_loans.py -x -q
uv run pytest -k "race or failed"
```

`uv run` puts the project's `dev` group on the path, so `pytest` and `httpx2`
come from the same environment the app runs in.

## Database assumptions

| Thing | Value |
|---|---|
| Database | `library_test`, **separate** from `library` |
| URL source | `TEST_DATABASE_URL`, from the environment or `.env` |
| Schema | built by `alembic upgrade head`, once per session |
| Between tests | `TRUNCATE … RESTART IDENTITY CASCADE` |
| Business rules | 14 days, 3 loans, 50 kobo/day, 2000 kobo cap |

`.env.example` already carries the line:

```
TEST_DATABASE_URL=postgresql+psycopg://gamp:gamp@127.0.0.1:5432/library_test
```

The suite **refuses to start** if `TEST_DATABASE_URL` is missing, equals
`DATABASE_URL`, or does not contain `test`. Truncation is destructive and this
is the only guard against running it against `library`.

It also stops if `.env` overrides the business rules, because the tests assert
those numbers and a silent change would turn a real failure into a confusing
one.

## What has to exist before anything runs

`app/main.py`, exporting `app`. Until it lands the whole suite errors at the
first fixture with one message, not a stack trace. Every test is written from
`docs/api/openapi.yaml`, so it can be written **before** the routes exist —
that is the point of owning the harness.

## Layout

| File | Proves |
|---|---|
| `conftest.py` | test DB wiring, migrated schema, truncation, clients, factories |
| `helpers.py` | envelope assertions, direct-SQL setup, failure injection |
| `test_health.py` | `/health/ready` 200, and 503 `DATABASE_UNAVAILABLE` with the DB down |
| `test_catalog.py` | duplicate ISBN/barcode, ISBN pattern, 404s, search, paging |
| `test_members.py` | PATCH contract (omitted / null / blank), suspend + reactivate, 409s |
| `test_loans.py` | 404-before-409, `due_at = borrowed_at + 336h`, loan limit, filters |
| `test_fines.py` | started-24h ceiling, 2000 cap, no fine on time, payments, overpayment |
| `test_concurrency.py` | two sessions racing one copy, member racing the limit |
| `test_atomicity.py` | an injected mid-request failure leaves neither write behind |

## Two things worth knowing

**`422` is not the error envelope.** Pydantic validation failures come back as
FastAPI's own `{"detail": …}`; the spec defines no body for 422. Only the
documented 4xx/5xx errors are asserted to be `{"code", "message"}`.

**Race tests need concurrent threads, not concurrent coroutines.** They pass
only if the routes are `def` (threadpool) or the DB does the arbitration:
conditional `UPDATE … WHERE status = 'available'` for the copy, `SELECT … FOR
UPDATE` on the member for the loan limit, and `IntegrityError` translated to
`409`. With `async def` routes doing blocking driver calls, the two requests
serialise and the test passes for the wrong reason.

## Handover to CI (Member 5)

```bash
createdb library_test          # once, on the CI box
uv sync --group dev
TEST_DATABASE_URL=postgresql+psycopg://…/library_test uv run pytest -q
```

No server is started: `TestClient` drives the ASGI app in-process. The only
service CI needs is Postgres.
