from urllib.parse import quote

from fastapi import APIRouter, Response

from app.routers.dependencies import Db, Id, resolve
from app.schemas.common import Error
from app.schemas.loans import CreatedLoan, Loan, LoanCreate, ReturnResult

router = APIRouter(tags=["Loans"])


@router.post(
    "/loans",
    operation_id="borrowCopy",
    response_model=CreatedLoan,
    status_code=201,
    responses={
        404: {"model": Error},
        409: {"model": Error},
        422: {"model": Error},
        201: {"headers": {"Location": {"schema": {"type": "string"}}}},
    },
)
def borrow_copy(session: Db, response: Response, body: LoanCreate) -> CreatedLoan:
    result = resolve("loans", "borrow_copy")(session, **body.model_dump(exclude_unset=True))
    payload = CreatedLoan.model_validate(result)
    response.headers["Location"] = "/v1/loans/" + quote(str(payload.id), safe="")
    return payload


@router.get(
    "/loans/{loan_id}",
    operation_id="getLoan",
    response_model=Loan,
    status_code=200,
    responses={404: {"model": Error}, 422: {"model": Error}},
)
def get_loan(session: Db, loan_id: Id) -> Loan:
    result = resolve("loans", "get_loan")(session, loan_id)
    payload = Loan.model_validate(result)
    return payload


@router.post(
    "/loans/{loan_id}/return",
    operation_id="returnLoan",
    response_model=ReturnResult,
    status_code=200,
    responses={404: {"model": Error}, 409: {"model": Error}, 422: {"model": Error}},
)
def return_loan(session: Db, loan_id: Id) -> ReturnResult:
    result = resolve("loans", "return_loan")(session, loan_id)
    payload = ReturnResult.model_validate(result)
    return payload
