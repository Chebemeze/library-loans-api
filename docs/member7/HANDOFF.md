# Member 7 | Pydantic models and validation errors

**Base:** the completed Member 6 routing implementation, not a bare `develop` checkout. The ZIP contains only files changed or added for Member 7. Unchanged M6 files (including the shared DomainError interface) remain required. No remote push has been made.

## Ownership and decisions

- Models remain under `app.schemas.{books,copies,members,loans,fines,common}`. M6's existing router imports remain valid. M7 owns the public request/response shapes, not the storage models or lending policy.
- `BookCreate` validates unhyphenated ISBN-10/13 **format**, without introducing a checksum rule. Authors remain ordered and unique. Inputs reject extra fields; current whitespace normalization is retained.
- `MemberUpdate` requires at least one property; omitting a property leaves it alone. An explicit null clears phone, never name. The generated schema now describes these rules as well as the runtime validators.
- Loan creation accepts only the copy barcode and member UUID. M1 computes the due date. `Loan` accepts ORM attributes, requires nullable `returned_at`, rejects naive timestamps, normalizes offsets to UTC, checks due time is later than borrowing and return time is not earlier. It does not enforce the configured loan duration on historical responses.
- Creation receipts are closed output models: mappings must contain just the contracted identifier. Full resource responses expose their public fields. Amounts exposed by the payment input are positive integer kobo, not strings, booleans or floats.
- Malformed JSON or invalid body, path or query → 422 `{code: INVALID_INPUT, message: ...}`. Known service exceptions retain their documented 404/409 mappings. Bad service output is a server bug, **not** a request-validation error. `SERVICE_NOT_CONFIGURED` remains M6's temporary integration signal, not a new published domain error.
- The only M3-owned file touched is `app/routers/health.py`: attach `Health`/`Error` schemas to the existing route and return a validated success model. Its SQL probe and status behavior are unchanged. Coordinate that small change with M3.

## Branch and stage

1. Start on the merged M6 baseline (or on the M6 branch for a stacked PR). Create `validation` with `git switch -c validation`.
2. Extract the ZIP at the project root (beside `pyproject.toml`); merge folders, do not delete them. If teammates have changed overlapping files, reconcile the differences before copying.
3. Stage only this delta:

```sh
git add -- app/schemas/{common,books,copies,members,loans,fines}.py \
  app/routers/{errors,health}.py tests/member7/test_validation.py docs/member7/HANDOFF.md
git diff --cached --stat
```

## Verify before pushing

```sh
uv sync --locked --group dev --no-install-project
uv run python -m pytest -q tests/member7
uv run python -m pytest -q tests
uv run ruff check app tests
uv run mypy app
```

Recorded: **22 Member 7 tests**, **51 total passed**, **4 opt-in M6 database/live-server tests skipped** (no configured test DB or running API for this run). One pre-existing Starlette/httpx deprecation warning. Ruff and strict mypy passed. These results do not establish production database integration. Re-enable M6's opt-in checks using `docs/member6/TEST-REPORT.md` on the integrated branch.

After review: `git commit -m "Align Pydantic schemas and validation errors with the API contract"` and `git push -u origin member7/validation`. Target the M6 branch if it has not merged; otherwise target `develop`. Disclose AI assistance per the project policy. Do not commit ZIPs or the virtual environment.
