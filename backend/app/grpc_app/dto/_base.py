from __future__ import annotations

from typing import Self

from google.protobuf import message as _message
from pydantic import BaseModel, ConfigDict


class _DTO(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def from_proto(cls, req: _message.Message) -> Self:
       return cls(
            **{field.name: value for field, value in req.ListFields()},
        )
