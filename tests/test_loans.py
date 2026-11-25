"""Borrowing: the rules, the order they are checked in, and the 14-day due date.

Order matters as much as the outcomes. A missing copy or member must be a 404
even when the member would also have been blocked, because that is the
difference between "wrong barcode" and "go away" for the librarian at the desk.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from helpers import (
    LOAN_PERIOD,
    assert_error,
    assert_only,
    count_open_loans,
    make_loan_late,
    parse_dt,
    withdraw_copy,
)


def test_borrow_returns_only_the_loan_id(
    client: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    isbn = make_book()
    barcode = make_copy(isbn)
    member_id = make_member()

    loan = borrow(barcode, member_id)

    assert_only({"id": loan["id"]}, {"id"})
    assert client.get(f"/v1/loans/{loan['id']}").status_code == 200


def test_due_date_is_borrowed_plus_336_hours(
    client: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    isbn = make_book()
    barcode = make_copy(isbn)
    member_id = make_member()

    loan_id = borrow(barcode, member_id)["id"]
    body = client.get(f"/v1/loans/{loan_id}").json()

    borrowed_at = parse_dt(body["borrowed_at"])
    due_at = parse_dt(body["due_at"])

    assert due_at - borrowed_at == LOAN_PERIOD
    assert body["returned_at"] is None
    assert body["copy_barcode"] == barcode
    assert body["member_id"] == member_id


def test_borrow_marks_the_copy_on_loan(
    client: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    isbn = make_book()
    barcode = make_copy(isbn)
    borrow(barcode, make_member())

    assert client.get(f"/v1/copies/{barcode}").json()["status"] == "on_loan"


def test_location_header_points_at_the_loan(
    client: Any, make_book: Any, make_copy: Any, make_member: Any
) -> None:
    isbn = make_book()
    barcode = make_copy(isbn)

    response = client.post(
        "/v1/loans", json={"copy_barcode": barcode, "member_id": make_member()}
    )

    assert response.status_code == 201, response.text
    location = response.headers.get("location")
    assert location, "POST /v1/loans must send a Location header"
    assert client.get(location).status_code == 200


def test_unknown_copy_is_404(
    make_book: Any, make_copy: Any, make_member: Any, post_loan: Any
) -> None:
    member_id = make_member()

    response = post_loan("NO-SUCH-COPY", member_id)

    assert_error(response, 404, "COPY_NOT_FOUND")


def test_unknown_member_is_404(make_book: Any, make_copy: Any, post_loan: Any) -> None:
    barcode = make_copy(make_book())

    response = post_loan(barcode, str(uuid.uuid4()))

    assert_error(response, 404, "MEMBER_NOT_FOUND")


def test_missing_copy_wins_over_a_blocked_member(
    client: Any, make_book: Any, make_copy: Any, make_member: Any, post_loan: Any
) -> None:
    """404 before 409: a bad barcode is a lookup failure, not a rule violation."""
    member_id = make_member()
    client.post(f"/v1/members/{member_id}/suspend")

    response = post_loan("NO-SUCH-COPY", member_id)

    assert_error(response, 404, "COPY_NOT_FOUND")


def test_missing_member_wins_over_a_busy_copy(
    make_book: Any, make_copy: Any, make_member: Any, borrow: Any, post_loan: Any
) -> None:
    barcode = make_copy(make_book())
    borrow(barcode, make_member())

    response = post_loan(barcode, str(uuid.uuid4()))

    assert_error(response, 404, "MEMBER_NOT_FOUND")


def test_copy_already_on_loan_is_409(
    make_book: Any, make_copy: Any, make_member: Any, borrow: Any, post_loan: Any
) -> None:
    barcode = make_copy(make_book())
    borrow(barcode, make_member())

    assert_error(post_loan(barcode, make_member()), 409, "NO_COPY_AVAILABLE")


def test_repeat_borrow_is_not_idempotent(
    make_book: Any, make_copy: Any, make_member: Any, borrow: Any, post_loan: Any
) -> None:
    """Decision Q10: the same request twice is a conflict, not a replay."""
    barcode = make_copy(make_book())
    member_id = make_member()
    borrow(barcode, member_id)

    assert_error(post_loan(barcode, member_id), 409, "NO_COPY_AVAILABLE")


def test_withdrawn_copy_is_409(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, post_loan: Any
) -> None:
    barcode = make_copy(make_book())
    withdraw_copy(db, barcode)

    assert_error(post_loan(barcode, make_member()), 409, "NO_COPY_AVAILABLE")


def test_suspended_member_is_409(
    client: Any, make_book: Any, make_copy: Any, make_member: Any, post_loan: Any
) -> None:
    member_id = make_member()
    client.post(f"/v1/members/{member_id}/suspend")

    assert_error(post_loan(make_copy(make_book()), member_id), 409, "MEMBER_BLOCKED")


def test_fourth_open_loan_is_409(
    make_book: Any, make_copy: Any, make_member: Any, borrow: Any, post_loan: Any
) -> None:
    isbn = make_book()
    codes = [make_copy(isbn) for _ in range(4)]
    member_id = make_member()

    for barcode in codes[:3]:
        borrow(barcode, member_id)

    assert_error(post_loan(codes[3], member_id), 409, "LOAN_LIMIT")


def test_returning_a_loan_makes_room_again(
    client: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    isbn = make_book()
    codes = [make_copy(isbn) for _ in range(4)]
    member_id = make_member()
    loans = [borrow(barcode, member_id) for barcode in codes[:3]]

    client.post(f"/v1/loans/{loans[0]['id']}/return")

    response = client.post(
        "/v1/loans", json={"copy_barcode": codes[3], "member_id": member_id}
    )
    assert response.status_code == 201, response.text


def test_an_overdue_open_loan_does_not_block_borrowing(
    make_book: Any, make_copy: Any, make_member: Any, borrow: Any, post_loan: Any, db: Any
) -> None:
    """MEMBER_BLOCKED is suspension or unpaid fines -- not lateness while open."""
    isbn = make_book()
    first, second = make_copy(isbn), make_copy(isbn)
    member_id = make_member()
    loan = borrow(first, member_id)
    make_loan_late(db, loan["id"], timedelta(days=9))

    assert post_loan(second, member_id).status_code == 201


def test_unpaid_fine_blocks_and_paying_it_unblocks(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any,
    post_loan: Any,
) -> None:
    isbn = make_book()
    first, second = make_copy(isbn), make_copy(isbn)
    member_id = make_member()

    loan = borrow(first, member_id)
    make_loan_late(db, loan["id"], timedelta(days=5))
    returned = client.post(f"/v1/loans/{loan['id']}/return").json()
    assert returned["fine_kobo"] == 250  # five started days at 50 kobo

    assert_error(post_loan(second, member_id), 409, "MEMBER_BLOCKED")

    fine_id = client.get(f"/v1/members/{member_id}/fines").json()["items"][0]["id"]
    paid = client.post(f"/v1/fines/{fine_id}/payments", json={"amount_kobo": 250})
    assert paid.status_code == 201, paid.text

    assert post_loan(second, member_id).status_code == 201


def test_returned_loan_frees_the_copy(
    client: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any, post_loan: Any
) -> None:
    barcode = make_copy(make_book())
    loan = borrow(barcode, make_member())

    client.post(f"/v1/loans/{loan['id']}/return")

    assert client.get(f"/v1/copies/{barcode}").json()["status"] == "available"
    assert post_loan(barcode, make_member()).status_code == 201


def test_unknown_loan_is_404(client: Any) -> None:
    assert_error(client.get("/v1/loans/99999"), 404, "LOAN_NOT_FOUND")


def test_member_loans_filter_by_open(
    client: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any, db: Any
) -> None:
    isbn = make_book()
    member_id = make_member()
    open_loan = borrow(make_copy(isbn), member_id)
    closed_loan = borrow(make_copy(isbn), member_id)
    client.post(f"/v1/loans/{closed_loan['id']}/return")

    all_loans = client.get(f"/v1/members/{member_id}/loans").json()["items"]
    open_only = client.get(f"/v1/members/{member_id}/loans", params={"open": "true"}).json()[
        "items"
    ]
    returned_only = client.get(
        f"/v1/members/{member_id}/loans", params={"open": "false"}
    ).json()["items"]

    assert len(all_loans) == 2
    assert [loan["id"] for loan in open_only] == [open_loan["id"]]
    assert [loan["id"] for loan in returned_only] == [closed_loan["id"]]
    assert count_open_loans(db, member_id=member_id) == 1
