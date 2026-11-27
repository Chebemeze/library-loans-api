from datetime import UTC, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import AfterValidator, AwareDatetime, Field, model_validator

from app.schemas.common import Barcode, ClosedOutput, Input, Output, Positive


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UtcTimestamp = Annotated[AwareDatetime, AfterValidator(_utc)]


class LoanCreate(Input):
    copy_barcode: Barcode
    member_id: UUID


class CreatedLoan(ClosedOutput):
    id: Positive


class Loan(Output):
    id: Positive
    member_id: UUID
    copy_barcode: str
    borrowed_at: UtcTimestamp
    due_at: UtcTimestamp
    returned_at: UtcTimestamp | None

    @model_validator(mode="after")
    def ordered_times(self) -> Self:
        if self.due_at <= self.borrowed_at:
            raise ValueError("due_at must be after borrowed_at")
        if self.returned_at is not None and self.returned_at < self.borrowed_at:
            raise ValueError("returned_at must not precede borrowed_at")
        return self


class LoanPage(Output):
    items: list[Loan]
    limit: int
    offset: int


class ReturnResult(Output):
    loan: Loan
    fine_kobo: Annotated[int, Field(ge=0)]
