from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Positive = Annotated[int, Field(ge=1)]
Barcode = Annotated[str, Field(min_length=1, max_length=64)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
ISBN_PATTERN = r"^(?:[0-9]{9}[0-9X]|[0-9]{13})$"


class ClosedOutput(Output):
    model_config = ConfigDict(extra="forbid")


ErrorCode = Literal[
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
]


class Error(ClosedOutput):
    code: ErrorCode
    message: str


class Health(Output):
    status: Literal["ready"]
