"""Fines: the ceiling rule, the cap, and payments.

Money is integer kobo everywhere. A fine is 50 kobo per late day, where a
"day" is a *started* 24-hour period after ``due_at`` -- one second late is
already one day -- and the whole fine is capped at 2000 kobo per loan.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from helpers import (
    assert_error,
    copy_status,
    count_rows,
    loan_row,
    make_loan_late,
)
from sqlalchemy import text


def _return_late(
    client: Any,
    db: Any,
    make_book: Any,
    make_copy: Any,
    make_member: Any,
    borrow: Any,
    late_by: timedelta,
) -> tuple[Any, int, str]:
    """Borrow a copy, push its due date into the past, then return it."""
    barcode = make_copy(make_book())
    member_id = make_member()
    loan = borrow(barcode, member_id)
    make_loan_late(db, loan["id"], late_by)
    response = client.post(f"/v1/loans/{loan['id']}/return")
    return response, int(loan["id"]), barcode


def test_on_time_return_raises_no_fine(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    barcode = make_copy(make_book())
    loan = borrow(barcode, make_member())

    response = client.post(f"/v1/loans/{loan['id']}/return")

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"loan", "fine_kobo"}
    assert body["fine_kobo"] == 0
    assert body["loan"]["returned_at"] is not None
    assert count_rows(db, "fines") == 0
    assert copy_status(db, barcode) == "available"


def test_one_second_late_is_already_one_day(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    response, loan_id, _ = _return_late(
        client, db, make_book, make_copy, make_member, borrow, timedelta(seconds=1)
    )

    assert response.status_code == 200, response.text
    assert response.json()["fine_kobo"] == 50
    assert count_rows(db, "fines", loan_id=loan_id) == 1


def test_ninety_minutes_late_is_still_one_day(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    response, _, _ = _return_late(
        client, db, make_book, make_copy, make_member, borrow, timedelta(minutes=90)
    )

    assert response.json()["fine_kobo"] == 50


def test_twenty_five_hours_late_is_two_days(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    response, _, _ = _return_late(
        client, db, make_book, make_copy, make_member, borrow, timedelta(hours=25)
    )

    assert response.json()["fine_kobo"] == 100


def test_fine_is_capped_at_2000_kobo(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    """60 days at 50 kobo is 3050, so the cap has to bite."""
    response, _, _ = _return_late(
        client, db, make_book, make_copy, make_member, borrow, timedelta(days=60)
    )

    assert response.json()["fine_kobo"] == 2000


def test_return_records_one_fine_row_at_the_reported_amount(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    response, loan_id, _ = _return_late(
        client, db, make_book, make_copy, make_member, borrow, timedelta(days=2)
    )

    reported = response.json()["fine_kobo"]
    stored = db.execute(
        text("SELECT amount_kobo FROM fines WHERE loan_id = :id"),
        {"id": loan_id},
    ).scalar_one()
    assert reported == stored == 100


def test_loan_row_is_closed_by_the_return(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    response, loan_id, barcode = _return_late(
        client, db, make_book, make_copy, make_member, borrow, timedelta(days=1)
    )

    row = loan_row(db, loan_id)
    assert row.returned_at is not None
    assert copy_status(db, barcode) == "available"
    assert response.json()["loan"]["returned_at"] is not None


def test_second_return_is_409_and_raises_no_second_fine(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    response, loan_id, _ = _return_late(
        client, db, make_book, make_copy, make_member, borrow, timedelta(days=3)
    )
    assert response.status_code == 200, response.text

    again = client.post(f"/v1/loans/{loan_id}/return")

    assert_error(again, 409, "ALREADY_RETURNED")
    assert count_rows(db, "fines", loan_id=loan_id) == 1


def test_partial_payments_add_up(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    barcode = make_copy(make_book())
    member_id = make_member()
    loan = borrow(barcode, member_id)
    make_loan_late(db, loan["id"], timedelta(days=2))
    client.post(f"/v1/loans/{loan['id']}/return")

    fine = client.get(f"/v1/members/{member_id}/fines").json()["items"][0]
    assert (fine["amount_kobo"], fine["paid_kobo"]) == (100, 0)

    first = client.post(f"/v1/fines/{fine['id']}/payments", json={"amount_kobo": 40})
    assert first.status_code == 201, first.text
    assert set(first.json()) == {"id"}
    assert client.get(f"/v1/members/{member_id}/fines").json()["items"][0]["paid_kobo"] == 40

    second = client.post(f"/v1/fines/{fine['id']}/payments", json={"amount_kobo": 60})
    assert second.status_code == 201, second.text
    assert client.get(f"/v1/members/{member_id}/fines").json()["items"][0]["paid_kobo"] == 100


def test_overpayment_is_409(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    barcode = make_copy(make_book())
    member_id = make_member()
    loan = borrow(barcode, member_id)
    make_loan_late(db, loan["id"], timedelta(days=1))
    client.post(f"/v1/loans/{loan['id']}/return")

    fine = client.get(f"/v1/members/{member_id}/fines").json()["items"][0]
    over = fine["amount_kobo"] - fine["paid_kobo"] + 1

    assert_error(
        client.post(f"/v1/fines/{fine['id']}/payments", json={"amount_kobo": over}),
        409,
        "OVERPAYMENT",
    )
    assert client.get(f"/v1/members/{member_id}/fines").json()["items"][0]["paid_kobo"] == 0


def test_payment_amount_must_be_positive(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    barcode = make_copy(make_book())
    member_id = make_member()
    loan = borrow(barcode, member_id)
    make_loan_late(db, loan["id"], timedelta(days=1))
    client.post(f"/v1/loans/{loan['id']}/return")
    fine_id = client.get(f"/v1/members/{member_id}/fines").json()["items"][0]["id"]

    for amount in (0, -50):
        response = client.post(f"/v1/fines/{fine_id}/payments", json={"amount_kobo": amount})
        assert response.status_code == 422, f"{amount} was accepted"


def test_payment_on_unknown_fine_is_404(client: Any) -> None:
    response = client.post("/v1/fines/99999/payments", json={"amount_kobo": 50})

    assert_error(response, 404, "FINE_NOT_FOUND")


def test_fines_filter_by_unpaid(
    client: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    isbn = make_book()
    debtor = make_member(name="Ada Nwosu")
    payer = make_member(name="Bola Adeyemi")

    unpaid_loan = borrow(make_copy(isbn), debtor)
    make_loan_late(db, unpaid_loan["id"], timedelta(days=1))
    client.post(f"/v1/loans/{unpaid_loan['id']}/return")

    # A separate member, because an unpaid fine blocks further borrowing.
    paid_loan = borrow(make_copy(isbn), payer)
    make_loan_late(db, paid_loan["id"], timedelta(days=1))
    client.post(f"/v1/loans/{paid_loan['id']}/return")

    payer_fine = client.get(f"/v1/members/{payer}/fines").json()["items"][0]
    client.post(
        f"/v1/fines/{payer_fine['id']}/payments", json={"amount_kobo": payer_fine["amount_kobo"]}
    )

    unpaid = client.get(f"/v1/members/{debtor}/fines", params={"unpaid": "true"}).json()["items"]
    paid = client.get(f"/v1/members/{payer}/fines", params={"unpaid": "false"}).json()["items"]

    assert [fine["amount_kobo"] - fine["paid_kobo"] for fine in unpaid] == [50]
    assert [fine["paid_kobo"] for fine in paid] == [50]
