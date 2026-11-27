from typing import Literal

from app.schemas.common import Barcode, ClosedOutput, Input, Output


class CopyCreate(Input):
    barcode: Barcode


class CreatedCopy(ClosedOutput):
    barcode: str


class Copy(Output):
    barcode: str
    isbn: str
    status: Literal["available", "on_loan", "withdrawn"]
