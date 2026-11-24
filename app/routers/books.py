from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Query, Response

from app.routers.dependencies import Db, Isbn, Limit, Offset, resolve
from app.schemas.books import Book, BookCreate, BookPage, CreatedBook
from app.schemas.common import Error
from app.schemas.copies import CopyCreate, CreatedCopy

router = APIRouter(tags=["Books"])


@router.get(
    "/books",
    operation_id="searchBooks",
    response_model=BookPage,
    status_code=200,
    responses={422: {"model": Error}},
)
def search_books(
    session: Db,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> BookPage:
    result = resolve("catalog", "search_books")(session, search=search, limit=limit, offset=offset)
    payload = BookPage.model_validate(result)
    return payload


@router.post(
    "/books",
    operation_id="createBook",
    response_model=CreatedBook,
    status_code=201,
    responses={
        409: {"model": Error},
        422: {"model": Error},
        201: {"headers": {"Location": {"schema": {"type": "string"}}}},
    },
)
def create_book(session: Db, response: Response, body: BookCreate) -> CreatedBook:
    result = resolve("catalog", "create_book")(session, **body.model_dump(exclude_unset=True))
    payload = CreatedBook.model_validate(result)
    response.headers["Location"] = "/v1/books/" + quote(str(payload.isbn), safe="")
    return payload


@router.get(
    "/books/{isbn}",
    operation_id="getBook",
    response_model=Book,
    status_code=200,
    responses={404: {"model": Error}, 422: {"model": Error}},
)
def get_book(session: Db, isbn: Isbn) -> Book:
    result = resolve("catalog", "get_book")(session, isbn)
    payload = Book.model_validate(result)
    return payload


@router.post(
    "/books/{isbn}/copies",
    operation_id="addCopy",
    response_model=CreatedCopy,
    status_code=201,
    responses={
        404: {"model": Error},
        409: {"model": Error},
        422: {"model": Error},
        201: {"headers": {"Location": {"schema": {"type": "string"}}}},
    },
)
def add_copy(session: Db, response: Response, isbn: Isbn, body: CopyCreate) -> CreatedCopy:
    result = resolve("catalog", "add_copy")(session, isbn, **body.model_dump(exclude_unset=True))
    payload = CreatedCopy.model_validate(result)
    response.headers["Location"] = "/v1/copies/" + quote(str(payload.barcode), safe="")
    return payload
