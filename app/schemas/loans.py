from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.schemas.common import Barcode, Input, Output, Positive


class LoanCreate(Input):
    copy_barcode: Barcode
    member_id: UUID


class CreatedLoan(Output):
    id: Positive


class Loan(CreatedLoan):
    member_id: UUID
    copy_barcode: str
    borrowed_at: AwareDatetime
    due_at: AwareDatetime
    returned_at: AwareDatetime | None


class LoanPage(Output):
    items: list[Loan]
    limit: int
    offset: int


class ReturnResult(Output):
    loan: Loan
    fine_kobo: Annotated[int, Field(ge=0)]
