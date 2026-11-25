"""Helpers shared by the tests: time, assertions, direct SQL."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

# The 16 stable codes documented in docs/api/openapi.yaml under Error.code.
ERROR_CODES = frozenset(
    {
        "BOOK_NOT_FOUND",
        "COPY_NOT_FOUND",
        "MEMBER_NOT_FOUND",
        "LOAN_NOT_FOUND",
        "FINE_NOT_FOUND",
        "DUPLICATE_ISBN",
        "DUPLICATE_BARCODE",
        "NO_COPY_AVAILABLE",
        "LOAN_LIMIT",
        "MEMBER_BLOCKED",
        "ALREADY_SUSPENDED",
        "NOT_SUSPENDED",
        "ALREADY_RETURNED",
        "OVERPAYMENT",
        "INVALID_INPUT",
        "DATABASE_UNAVAILABLE",
    }
)

LOAN_PERIOD = timedelta(hours=336)


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


def parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None, f"{value!r} is not timezone-aware"
    return parsed.astimezone(UTC)


def assert_error(response: Any, status: int, code: str | None = None) -> dict[str, Any]:
    assert response.status_code == status, (
        f"expected {status}, got {response.status_code}: {response.text}"
    )
    assert response.headers["content-type"].startswith("application/json"), response.headers
    body = response.json()
    assert set(body) == {"code", "message"}, body
    assert isinstance(body["code"], str) and isinstance(body["message"], str), body
    assert body["message"].strip(), "message must say something"
    assert body["code"] in ERROR_CODES, f"{body['code']} is not a documented code"
    if code is not None:
        assert body["code"] == code, f"expected {code}, got {body['code']}: {body['message']}"
    return dict(body)


def assert_only(body: dict[str, Any], keys: set[str]) -> None:
    assert set(body) == keys, f"expected exactly {sorted(keys)}, got {sorted(body)}"


# --------------------------------------------------------------------------- #
# direct SQL: state the API cannot create
# --------------------------------------------------------------------------- #


def withdraw_copy(connection: Any, barcode: str) -> None:
    """Withdrawal is out of scope for v1.0.0, so the row is set by hand."""
    connection.execute(
        text("UPDATE copies SET status = 'withdrawn' WHERE barcode = :barcode"),
        {"barcode": barcode},
    )
    connection.commit()


def set_member_status(connection: Any, member_id: str, status: str) -> None:
    connection.execute(
        text("UPDATE members SET status = :status WHERE id = :id"),
        {"status": status, "id": uuid.UUID(member_id)},
    )
    connection.commit()


def make_loan_late(connection: Any, loan_id: int, late_by: timedelta) -> None:
    """Move a loan into the past so returning it is genuinely late.

    ``late_by`` is how late the return is, and the fine is exactly
    ``ceil(late_by / 1 day)`` days -- the same rule the API applies. A small
    slack (at most 30 minutes) is subtracted so that "2 days late" lands inside
    the second started day rather than a microsecond into the third, which is
    what would happen if the due date were moved back by exactly 2 days and the
    return request then arrived a moment later.

    Both timestamps move. ``ck_loans_due_after_borrow`` requires
    ``due_at > borrowed_at``, and a loan five days overdue was borrowed nineteen
    days ago, not today. The 336-hour gap is preserved.

    """
    slack = min(timedelta(minutes=30), late_by / 2)
    due_at = utcnow() - late_by + slack
    connection.execute(
        text("UPDATE loans SET borrowed_at = :borrowed_at, due_at = :due_at WHERE id = :id"),
        {"borrowed_at": due_at - LOAN_PERIOD, "due_at": due_at, "id": loan_id},
    )
    connection.commit()


def count_open_loans(
    connection: Any,
    copy_barcode: str | None = None,
    member_id: str | None = None,
) -> int:
    sql = "SELECT count(*) FROM loans WHERE returned_at IS NULL"
    params: dict[str, Any] = {}
    if copy_barcode is not None:
        sql += " AND copy_barcode = :barcode"
        params["barcode"] = copy_barcode
    if member_id is not None:
        sql += " AND member_id = :member_id"
        params["member_id"] = uuid.UUID(member_id)
    return int(connection.execute(text(sql), params).scalar_one())


def count_rows(connection: Any, table: str, **equals: Any) -> int:
    sql = f"SELECT count(*) FROM {table}"  # noqa: S608 - fixed table names in tests
    params: dict[str, Any] = {}
    if equals:
        clauses = []
        for key, value in equals.items():
            clauses.append(f"{key} = :{key}")
            params[key] = value
        sql += " WHERE " + " AND ".join(clauses)
    return int(connection.execute(text(sql), params).scalar_one())


def copy_status(connection: Any, barcode: str) -> str:
    return str(
        connection.execute(
            text("SELECT status FROM copies WHERE barcode = :barcode"), {"barcode": barcode}
        ).scalar_one()
    )


def loan_row(connection: Any, loan_id: int) -> Any:
    return connection.execute(
        text(
            "SELECT id, copy_barcode, member_id, borrowed_at, due_at, returned_at "
            "FROM loans WHERE id = :id"
        ),
        {"id": loan_id},
    ).one()


@contextmanager
def failing_writes(connection: Any, table: str, event: str = "UPDATE") -> Iterator[None]:
    """Make writes to ``table`` raise: a BEFORE trigger, so the failure lands
    inside the app's own transaction rather than around it."""
    name = "test_fail_" + uuid.uuid4().hex[:12]
    function_ddl = (
        f"CREATE FUNCTION {name}() RETURNS trigger AS $$ "
        f"BEGIN RAISE EXCEPTION 'injected failure on {table}'; END; "
        f"$$ LANGUAGE plpgsql"
    )
    trigger_ddl = (
        f"CREATE TRIGGER {name} BEFORE {event} ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION {name}()"
    )
    connection.execute(text(function_ddl))
    connection.execute(text(trigger_ddl))
    connection.commit()
    try:
        yield
    finally:
        connection.execute(text(f"DROP TRIGGER IF EXISTS {name} ON {table}"))
        connection.execute(text(f"DROP FUNCTION IF EXISTS {name}()"))
        connection.commit()
