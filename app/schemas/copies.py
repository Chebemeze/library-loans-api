from typing import Literal

from app.schemas.common import Barcode, Input, Output


class CopyCreate(Input):
    barcode: Barcode


class CreatedCopy(Output):
    barcode: str


class Copy(CreatedCopy):
    isbn: str
    status: Literal["available", "on_loan", "withdrawn"]
