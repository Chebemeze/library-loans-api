from fastapi import APIRouter

from app.routers.dependencies import Db, Id, resolve
from app.schemas.common import Error
from app.schemas.fines import CreatedPayment, PaymentCreate

router = APIRouter(tags=["Fines"])


@router.post(
    "/fines/{fine_id}/payments",
    operation_id="recordPayment",
    response_model=CreatedPayment,
    status_code=201,
    responses={404: {"model": Error}, 409: {"model": Error}, 422: {"model": Error}},
)
def record_payment(session: Db, fine_id: Id, body: PaymentCreate) -> CreatedPayment:
    result = resolve("fines", "record_payment")(
        session, fine_id, **body.model_dump(exclude_unset=True)
    )
    payload = CreatedPayment.model_validate(result)
    return payload
