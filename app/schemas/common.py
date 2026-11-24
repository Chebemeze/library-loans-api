from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Positive = Annotated[int, Field(ge=1)]
Barcode = Annotated[str, Field(min_length=1, max_length=64)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
ISBN_PATTERN = r"^(?:[0-9]{9}[0-9X]|[0-9]{13})$"


class Error(Output):
    code: str
    message: str
