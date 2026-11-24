from typing import Annotated

from pydantic import Field, field_validator

from app.schemas.common import ISBN_PATTERN, Input, Name, Output
from app.schemas.copies import Copy


class BookCreate(Input):
    isbn: Annotated[str, Field(pattern=ISBN_PATTERN)]
    title: Annotated[str, Field(min_length=1, max_length=300)]
    authors: Annotated[list[Name], Field(min_length=1, max_length=20)]

    @field_validator("authors")
    @classmethod
    def distinct(cls, names: list[str]) -> list[str]:
        if len(names) != len(set(names)):
            raise ValueError("authors must be unique")
        return names


class CreatedBook(Output):
    isbn: str


class BookSummary(CreatedBook):
    title: str
    authors: list[str]


class Book(BookSummary):
    copies: list[Copy]


class BookPage(Output):
    items: list[BookSummary]
    limit: int
    offset: int
