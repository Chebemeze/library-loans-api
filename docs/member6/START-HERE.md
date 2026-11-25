# Member 6 | Completed HTTP routing handoff

This folder is an overlay for the **root** of `library-loans-api` on `develop`, not the nested Docker copy. Make a feature branch, compare overlapping files before extraction, then review `git status`. No remote branch or PR has been created. The previous starter worksheets are superseded.

## Run

```sh
uv sync --locked --group dev
uv run python -m pytest -q tests/test_routes.py tests/test_wiring.py
uv run mypy app
uv run ruff check app tests
uv run uvicorn app.main:app --reload
```

Open `/docs`; for a DB-independent manual check try `GET /v1/loans/0` → 422 `INVALID_INPUT`. `/health/ready` is M3's actual PostgreSQL probe. M3's nested Docker build context must include this root `app/` tree. The only intentional API change to M3's router is its documented operation ID, `getReady`.


| HTTP operation ID | Service call | Result shape |
|---|---|---|
| `searchBooks` | `catalog.search_books(session, search=search, limit=limit, offset=offset)` | `BookPage` |
| `createBook` | `catalog.create_book(session, **submitted_fields)` | `CreatedBook` |
| `getBook` | `catalog.get_book(session, isbn)` | `Book` |
| `addCopy` | `catalog.add_copy(session, isbn, **submitted_fields)` | `CreatedCopy` |
| `getCopy` | `catalog.get_copy(session, barcode)` | `Copy` |
| `createMember` | `members.create_member(session, **submitted_fields)` | `CreatedMember` |
| `getMember` | `members.get_member(session, member_id)` | `Member` |
| `updateMember` | `members.update_member(session, member_id, **submitted_fields)` | `Member` |
| `suspendMember` | `members.suspend_member(session, member_id)` | `Member` |
| `reactivateMember` | `members.reactivate_member(session, member_id)` | `Member` |
| `listMemberLoans` | `members.list_member_loans(session, member_id, open_only=open_only, limit=limit, offset=offset)` | `LoanPage` |
| `listMemberFines` | `members.list_member_fines(session, member_id, unpaid=unpaid, limit=limit, offset=offset)` | `FinePage` |
| `borrowCopy` | `loans.borrow_copy(session, **submitted_fields)` | `CreatedLoan` |
| `getLoan` | `loans.get_loan(session, loan_id)` | `Loan` |
| `returnLoan` | `loans.return_loan(session, loan_id)` | `ReturnResult` |
| `recordPayment` | `fines.record_payment(session, fine_id, **submitted_fields)` | `CreatedPayment` |
`submitted_fields` means keyword arguments by their public schema names, never a positional request model. PATCH omits unsent keys but preserves `phone=None`. The public query flag `open` is forwarded internally as `open_only`.

## What was verified

Tests exercise each real HTTP handler with substituted service outputs: dispatch arguments, response body/status, creation headers, validation, domain errors and method/path/operation ID/response-status inventory against the checked-in YAML. No real loan was issued in these tests. The remaining integration gate belongs to the team: verify the same requests through M1/M8 against PostgreSQL, including concurrent borrowing and rollback. Review and disclose AI assistance in the PR; the project README also calls for owner-written core logic and a live walkthrough, so confirm with your lead before submitting an AI-authored implementation.
