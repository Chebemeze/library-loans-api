from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from app.schemas.common import ClosedOutput, Input, Name, Output

Phone = Annotated[str, Field(pattern=r"^\+?[0-9]{7,19}$", max_length=20)]


class MemberCreate(Input):
    name: Name
    phone: Phone | None = None


class MemberUpdate(Input):
    model_config = ConfigDict(json_schema_extra={"minProperties": 1})
    name: Name | SkipJsonSchema[None] = Field(default_factory=lambda: None)
    phone: Phone | None = None

    @model_validator(mode="after")
    def valid_patch(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("provide name or phone")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class CreatedMember(ClosedOutput):
    id: UUID


class Member(Output):
    id: UUID
    name: str
    phone: str | None
    status: Literal["active", "suspended"]
