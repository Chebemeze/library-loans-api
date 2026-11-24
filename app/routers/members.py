from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.routers.dependencies import Db, Limit, Offset, resolve
from app.schemas.common import Error
from app.schemas.fines import FinePage
from app.schemas.loans import LoanPage
from app.schemas.members import CreatedMember, Member, MemberCreate, MemberUpdate

router = APIRouter(tags=["Members"])


@router.post(
    "/members",
    operation_id="createMember",
    response_model=CreatedMember,
    status_code=201,
    responses={
        422: {"model": Error},
        201: {"headers": {"Location": {"schema": {"type": "string"}}}},
    },
)
def create_member(session: Db, response: Response, body: MemberCreate) -> CreatedMember:
    result = resolve("members", "create_member")(session, **body.model_dump(exclude_unset=True))
    payload = CreatedMember.model_validate(result)
    response.headers["Location"] = "/v1/members/" + quote(str(payload.id), safe="")
    return payload


@router.get(
    "/members/{member_id}",
    operation_id="getMember",
    response_model=Member,
    status_code=200,
    responses={404: {"model": Error}, 422: {"model": Error}},
)
def get_member(session: Db, member_id: UUID) -> Member:
    result = resolve("members", "get_member")(session, member_id)
    payload = Member.model_validate(result)
    return payload


@router.patch(
    "/members/{member_id}",
    operation_id="updateMember",
    response_model=Member,
    status_code=200,
    responses={404: {"model": Error}, 422: {"model": Error}},
)
def update_member(session: Db, member_id: UUID, body: MemberUpdate) -> Member:
    result = resolve("members", "update_member")(
        session, member_id, **body.model_dump(exclude_unset=True)
    )
    payload = Member.model_validate(result)
    return payload


@router.post(
    "/members/{member_id}/suspend",
    operation_id="suspendMember",
    response_model=Member,
    status_code=200,
    responses={404: {"model": Error}, 409: {"model": Error}, 422: {"model": Error}},
)
def suspend_member(session: Db, member_id: UUID) -> Member:
    result = resolve("members", "suspend_member")(session, member_id)
    payload = Member.model_validate(result)
    return payload


@router.post(
    "/members/{member_id}/reactivate",
    operation_id="reactivateMember",
    response_model=Member,
    status_code=200,
    responses={404: {"model": Error}, 409: {"model": Error}, 422: {"model": Error}},
)
def reactivate_member(session: Db, member_id: UUID) -> Member:
    result = resolve("members", "reactivate_member")(session, member_id)
    payload = Member.model_validate(result)
    return payload


@router.get(
    "/members/{member_id}/loans",
    operation_id="listMemberLoans",
    response_model=LoanPage,
    status_code=200,
    responses={404: {"model": Error}, 422: {"model": Error}},
)
def list_member_loans(
    session: Db,
    member_id: UUID,
    open_only: Annotated[bool | None, Query(alias="open")] = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> LoanPage:
    result = resolve("members", "list_member_loans")(
        session, member_id, open_only=open_only, limit=limit, offset=offset
    )
    payload = LoanPage.model_validate(result)
    return payload


@router.get(
    "/members/{member_id}/fines",
    operation_id="listMemberFines",
    response_model=FinePage,
    status_code=200,
    responses={404: {"model": Error}, 422: {"model": Error}},
)
def list_member_fines(
    session: Db,
    member_id: UUID,
    unpaid: Annotated[bool | None, Query()] = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> FinePage:
    result = resolve("members", "list_member_fines")(
        session, member_id, unpaid=unpaid, limit=limit, offset=offset
    )
    payload = FinePage.model_validate(result)
    return payload
