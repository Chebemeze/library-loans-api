"""Races that only appear when two requests are in flight at once.

These are the tests that fail on a check-then-insert implementation and pass on
one that lets the database arbitrate: a conditional ``UPDATE`` for the copy, a
row lock on the member for the loan limit, and a translation of the resulting
``IntegrityError`` into 409 rather than a 500.

They use ``httpx2.ASGITransport`` against the same app object, so no server is
needed. Two clients are used to make the intent obvious.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from helpers import count_open_loans
from sqlalchemy import text

pytestmark = pytest.mark.anyio


def _async_client(app: Any) -> Any:
    import httpx2

    return httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app), base_url="http://library.test"
    )


async def test_two_sessions_racing_one_copy_produce_one_loan(
    app: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any
) -> None:
    barcode = make_copy(make_book())
    member_a = make_member(name="Ada Nwosu")
    member_b = make_member(name="Bola Adeyemi")

    async with _async_client(app) as first, _async_client(app) as second:
        responses = await asyncio.gather(
            first.post("/v1/loans", json={"copy_barcode": barcode, "member_id": member_a}),
            second.post("/v1/loans", json={"copy_barcode": barcode, "member_id": member_b}),
        )

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [201, 409], [(r.status_code, r.text) for r in responses]

    loser = next(response for response in responses if response.status_code == 409)
    assert loser.json()["code"] == "NO_COPY_AVAILABLE"
    assert count_open_loans(db, copy_barcode=barcode) == 1


async def test_the_same_member_racing_twice_still_gets_one_loan(
    app: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any
) -> None:
    barcode = make_copy(make_book())
    member_id = make_member()

    async with _async_client(app) as first, _async_client(app) as second:
        responses = await asyncio.gather(
            first.post("/v1/loans", json={"copy_barcode": barcode, "member_id": member_id}),
            second.post("/v1/loans", json={"copy_barcode": barcode, "member_id": member_id}),
        )

    assert sorted(response.status_code for response in responses) == [201, 409]
    assert count_open_loans(db, copy_barcode=barcode) == 1


async def test_two_copies_racing_against_the_limit_never_exceed_three(
    app: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any
) -> None:
    """A member with two open loans races for two more copies: three, never four."""
    isbn = make_book()
    held = [make_copy(isbn) for _ in range(2)]
    raced = [make_copy(isbn) for _ in range(2)]
    member_id = make_member()

    for barcode in held:
        borrow(barcode, member_id)
    assert count_open_loans(db, member_id=member_id) == 2

    async with _async_client(app) as first, _async_client(app) as second:
        responses = await asyncio.gather(
            first.post("/v1/loans", json={"copy_barcode": raced[0], "member_id": member_id}),
            second.post("/v1/loans", json={"copy_barcode": raced[1], "member_id": member_id}),
        )

    assert sorted(response.status_code for response in responses) == [201, 409], [
        (r.status_code, r.text) for r in responses
    ]
    loser = next(response for response in responses if response.status_code == 409)
    assert loser.json()["code"] == "LOAN_LIMIT"
    assert count_open_loans(db, member_id=member_id) == 3


async def test_two_sessions_racing_one_copy_for_return_close_it_once(
    app: Any, db: Any, make_book: Any, make_copy: Any, make_member: Any, borrow: Any,
    client: Any,
) -> None:
    barcode = make_copy(make_book())
    loan = borrow(barcode, make_member())
    return_url = f"/v1/loans/{loan['id']}/return"

    async with _async_client(app) as first, _async_client(app) as second:
        responses = await asyncio.gather(first.post(return_url), second.post(return_url))

    assert sorted(response.status_code for response in responses) == [200, 409], [
        (r.status_code, r.text) for r in responses
    ]
    assert db.execute(text("SELECT count(*) FROM fines")).scalar_one() <= 1
