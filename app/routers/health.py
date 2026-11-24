"""Database-backed readiness endpoint for container and load-balancer probes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.db.session import get_session

router = APIRouter()


@router.get(
    "/health/ready",
    tags=["Health"],
    operation_id="getReady",
    summary="Ready only when the database answers",
    responses={503: {"description": "The database does not answer."}},
)
def readiness(session: Annotated[Session, Depends(get_session)]) -> JSONResponse:
    """Return ready only after a lightweight query succeeds on PostgreSQL."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "code": "DATABASE_UNAVAILABLE",
                "message": "The database did not answer.",
            },
        )

    return JSONResponse(status_code=200, content={"status": "ready"})
