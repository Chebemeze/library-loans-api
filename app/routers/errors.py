from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.common import Error
from app.services.errors import DomainError

NOT_FOUND = {
    "BOOK_NOT_FOUND",
    "COPY_NOT_FOUND",
    "MEMBER_NOT_FOUND",
    "LOAN_NOT_FOUND",
    "FINE_NOT_FOUND",
}
CONFLICT = {
    "DUPLICATE_ISBN",
    "DUPLICATE_BARCODE",
    "NO_COPY_AVAILABLE",
    "LOAN_LIMIT",
    "MEMBER_BLOCKED",
    "ALREADY_SUSPENDED",
    "NOT_SUSPENDED",
    "ALREADY_RETURNED",
    "OVERPAYMENT",
}


class MissingService(Exception):
    """A team service has not yet been integrated; never simulate success."""


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        error = exc.errors()[0]
        field = ".".join(map(str, error["loc"]))
        envelope = Error(code="INVALID_INPUT", message=f"{field}: {error['msg']}")
        return JSONResponse(envelope.model_dump(), 422)

    @app.exception_handler(DomainError)
    async def domain(request: Request, exc: DomainError) -> JSONResponse:
        if exc.code not in NOT_FOUND | CONFLICT:
            raise exc
        return JSONResponse(
            Error.model_validate({"code": exc.code, "message": str(exc)}).model_dump(),
            404 if exc.code in NOT_FOUND else 409,
        )

    @app.exception_handler(MissingService)
    async def unavailable(request: Request, exc: MissingService) -> JSONResponse:
        return JSONResponse({"code": "SERVICE_NOT_CONFIGURED", "message": str(exc)}, 503)
