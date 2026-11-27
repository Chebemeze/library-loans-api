from typing import Annotated

from pydantic import Field

from app.schemas.common import ClosedOutput, Input, Output, Positive


class Fine(Output):
    id: Positive
    loan_id: Positive
    amount_kobo: Annotated[int, Field(ge=1, le=2000)]
    paid_kobo: Annotated[int, Field(ge=0)]


class FinePage(Output):
    items: list[Fine]
    limit: int
    offset: int


class PaymentCreate(Input):
    amount_kobo: Annotated[int, Field(strict=True, ge=1)]


class CreatedPayment(ClosedOutput):
    id: Positive
