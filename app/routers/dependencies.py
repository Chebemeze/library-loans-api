"""Only integration boundary: import an owner's real service when its route runs."""

from collections.abc import Callable
from importlib import import_module
from typing import Annotated, cast

from fastapi import Depends, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.routers.errors import MissingService
from app.schemas.common import ISBN_PATTERN

Db = Annotated[Session, Depends(get_session)]
Isbn = Annotated[str, Path(pattern=ISBN_PATTERN)]
BarcodePath = Annotated[str, Path(min_length=1, max_length=64)]
Id = Annotated[int, Path(ge=1)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def resolve(module: str, name: str) -> Callable[..., object]:
    path = f"app.services.{module}"
    try:
        service = import_module(path)
    except ModuleNotFoundError as exc:
        if exc.name != path:
            raise
        raise MissingService(f"{path}.{name} is not installed.") from exc
    fn = getattr(service, name, None)
    if not callable(fn):
        raise MissingService(f"{path}.{name} is not installed.")
    return cast(Callable[..., object], fn)
