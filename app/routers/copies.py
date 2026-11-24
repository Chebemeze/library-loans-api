from fastapi import APIRouter

from app.routers.dependencies import BarcodePath, Db, resolve
from app.schemas.common import Error
from app.schemas.copies import Copy

router = APIRouter(tags=["Copies"])


@router.get(
    "/copies/{barcode}",
    operation_id="getCopy",
    response_model=Copy,
    status_code=200,
    responses={404: {"model": Error}, 422: {"model": Error}},
)
def get_copy(session: Db, barcode: BarcodePath) -> Copy:
    result = resolve("catalog", "get_copy")(session, barcode)
    payload = Copy.model_validate(result)
    return payload
