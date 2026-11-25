"""Catalogue: books, copies, search and paging.

Uniqueness here is the ISBN and the barcode, not an integer id, so the
duplicate tests are about database constraints surfacing as 409 rather than a
500 from an uncaught IntegrityError.
"""

from __future__ import annotations

from typing import Any

from helpers import assert_error, assert_only


def test_create_book_returns_only_the_isbn(client: Any, make_book: Any) -> None:
    isbn = make_book(title="Things Fall Apart", authors=("Chinua Achebe",))

    response = client.get(f"/v1/books/{isbn}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["isbn"] == isbn
    assert body["title"] == "Things Fall Apart"
    assert body["authors"] == ["Chinua Achebe"]
    assert body["copies"] == []


def test_create_book_body_is_only_the_id(client: Any) -> None:
    response = client.post(
        "/v1/books",
        json={"isbn": "9780306406157", "title": "Clean Code", "authors": ["Robert Martin"]},
    )

    assert response.status_code == 201, response.text
    assert_only(response.json(), {"isbn"})


def test_duplicate_isbn_is_409(client: Any, make_book: Any) -> None:
    isbn = make_book()

    response = client.post(
        "/v1/books", json={"isbn": isbn, "title": "Another Title", "authors": ["Someone Else"]}
    )

    assert_error(response, 409, "DUPLICATE_ISBN")


def test_isbn_pattern_is_enforced(client: Any) -> None:
    for bad_isbn in ("978-0-306-40615-7", "12345", "978030640615X"):
        response = client.post(
            "/v1/books", json={"isbn": bad_isbn, "title": "Bad", "authors": ["A"]}
        )
        assert response.status_code == 422, f"{bad_isbn} was accepted: {response.text}"


def test_book_title_and_authors_are_validated(client: Any) -> None:
    assert client.post(
        "/v1/books", json={"isbn": "9780306406157", "title": "   ", "authors": ["A"]}
    ).status_code == 422

    assert client.post(
        "/v1/books", json={"isbn": "9780306406157", "title": "Ok", "authors": []}
    ).status_code == 422


def test_unknown_book_is_404(client: Any) -> None:
    response = client.get("/v1/books/9780306406157")

    assert_error(response, 404, "BOOK_NOT_FOUND")


def test_create_copy_returns_only_the_barcode(client: Any, make_book: Any) -> None:
    isbn = make_book()

    response = client.post(f"/v1/books/{isbn}/copies", json={"barcode": "BC-0001"})

    assert response.status_code == 201, response.text
    assert_only(response.json(), {"barcode"})


def test_copy_starts_available_and_is_readable(client: Any, make_book: Any, make_copy: Any) -> None:
    isbn = make_book()
    barcode = make_copy(isbn)

    response = client.get(f"/v1/copies/{barcode}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {"barcode": barcode, "isbn": isbn, "status": "available"}


def test_book_reads_back_with_its_copies(client: Any, make_book: Any, make_copy: Any) -> None:
    isbn = make_book()
    make_copy(isbn, "BC-A")
    make_copy(isbn, "BC-B")

    body = client.get(f"/v1/books/{isbn}").json()

    assert {copy["barcode"] for copy in body["copies"]} == {"BC-A", "BC-B"}
    assert all(copy["status"] == "available" for copy in body["copies"])


def test_duplicate_barcode_is_409(client: Any, make_book: Any, make_copy: Any) -> None:
    isbn = make_book()
    barcode = make_copy(isbn)

    response = client.post(f"/v1/books/{isbn}/copies", json={"barcode": barcode})

    assert_error(response, 409, "DUPLICATE_BARCODE")


def test_copy_for_unknown_book_is_404(client: Any) -> None:
    response = client.post("/v1/books/9780306406157/copies", json={"barcode": "BC-0002"})

    assert_error(response, 404, "BOOK_NOT_FOUND")


def test_unknown_copy_is_404(client: Any) -> None:
    response = client.get("/v1/copies/NOPE")

    assert_error(response, 404, "COPY_NOT_FOUND")


def test_book_search_is_a_case_insensitive_substring_of_title_or_author(
    client: Any, make_book: Any
) -> None:
    make_book(title="The Long Afternoon", authors=("Ada Nwosu",))
    make_book(title="Salt and Honey", authors=("Bola Adeyemi",))
    make_book(title="Quiet Lagos", authors=("Ada Nwosu",))

    by_title = client.get("/v1/books", params={"search": "honey"}).json()
    by_author = client.get("/v1/books", params={"search": "ada nwosu"}).json()

    assert [item["title"] for item in by_title["items"]] == ["Salt and Honey"]
    assert {item["title"] for item in by_author["items"]} == {
        "The Long Afternoon",
        "Quiet Lagos",
    }


def test_books_page_in_title_then_isbn_order(client: Any, make_book: Any) -> None:
    make_book(isbn="9780306406157", title="Zebra")
    make_book(isbn="9780306406165", title="Apple")
    make_book(isbn="9780306406173", title="Apple")

    body = client.get("/v1/books").json()

    keys = [(item["title"], item["isbn"]) for item in body["items"]]
    assert keys == sorted(keys)
    assert keys[0] == ("Apple", "9780306406165")


def test_paging_echoes_limit_and_offset_without_overlapping(
    client: Any, make_book: Any
) -> None:
    for title in ("Alpha", "Bravo", "Charlie"):
        make_book(title=title)

    first = client.get("/v1/books", params={"limit": 2, "offset": 0}).json()
    second = client.get("/v1/books", params={"limit": 2, "offset": 2}).json()

    assert (first["limit"], first["offset"]) == (2, 0)
    assert (second["limit"], second["offset"]) == (2, 2)
    assert len(first["items"]) == 2
    assert len(second["items"]) == 1

    first_ids = {item["isbn"] for item in first["items"]}
    second_ids = {item["isbn"] for item in second["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_paging_defaults_are_20_and_0(client: Any) -> None:
    body = client.get("/v1/books").json()

    assert (body["limit"], body["offset"]) == (20, 0)


def test_limit_above_100_is_422(client: Any) -> None:
    assert client.get("/v1/books", params={"limit": 101}).status_code == 422
    assert client.get("/v1/books", params={"limit": 0}).status_code == 422
    assert client.get("/v1/books", params={"offset": -1}).status_code == 422
