"""Multi-write requests must leave the database in one state or the other.

A borrow touches two tables, a return three. If the second write fails after the
first is committed, the library loses a copy or raises a fine nobody can find.
"""

from __future__ import annotations

from typing import Any

from helpers import copy_status, count_open_loans, count_rows, failing_writes, loan_row


def test_failed_borrow_leaves_neither_a_loan_nor_a_held_copy(
    raw_client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any
) -> None:
    barcode = make_copy(make_book())
    member_id = make_member()

    with failing_writes(db, "copies", "UPDATE"):
        response = raw_client.post(
            "/v1/loans", json={"copy_barcode": barcode, "member_id": member_id}
        )

    assert response.status_code >= 400, (
        f"the injected failure must not look like success: {response.status_code}"
    )
    assert response.status_code != 201
    assert count_open_loans(db, copy_barcode=barcode) == 0
    assert count_rows(db, "loans") == 0
    assert copy_status(db, barcode) == "available"


def test_failed_return_leaves_the_loan_open_and_the_copy_held(
    raw_client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    barcode = make_copy(make_book())
    loan = borrow(barcode, make_member())

    # An on-time return writes no fine, so the failure is injected on the first
    # write (closing the loan) rather than on a fine that never happens.
    with failing_writes(db, "loans", "UPDATE"):
        response = raw_client.post(f"/v1/loans/{loan['id']}/return")

    assert response.status_code >= 400, response.text
    assert response.status_code != 200
    row = loan_row(db, int(loan["id"]))
    assert row.returned_at is None, "the loan was closed even though the return failed"
    assert copy_status(db, barcode) == "on_loan"
    assert count_rows(db, "fines") == 0


def test_failed_return_on_a_late_loan_does_not_half_close_it(
    raw_client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    from datetime import timedelta

    from helpers import make_loan_late

    barcode = make_copy(make_book())
    member_id = make_member()
    loan = borrow(barcode, member_id)
    make_loan_late(db, loan["id"], timedelta(days=4))

    with failing_writes(db, "fines", "INSERT"):
        response = raw_client.post(f"/v1/loans/{loan['id']}/return")

    assert response.status_code >= 400
    assert loan_row(db, int(loan["id"])).returned_at is None
    assert copy_status(db, barcode) == "on_loan"
    assert count_rows(db, "fines") == 0


def test_the_same_flow_succeeds_once_the_injected_failure_is_gone(
    raw_client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any
) -> None:
    """Control for the two tests above: same requests, nothing broken."""
    barcode = make_copy(make_book())
    member_id = make_member()

    with failing_writes(db, "copies", "UPDATE"):
        pass

    response = raw_client.post(
        "/v1/loans", json={"copy_barcode": barcode, "member_id": member_id}
    )

    assert response.status_code == 201, response.text
    assert count_open_loans(db, copy_barcode=barcode) == 1
