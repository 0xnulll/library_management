from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import pydantic

from app.domain.exceptions import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


def parse_or_invalid(dto_cls: Callable[..., T], **kwargs: object) -> T:
    """Construct *dto_cls* and re-raise Pydantic errors as domain ValidationError."""
    try:
        return dto_cls(**kwargs)
    except pydantic.ValidationError as exc:
        messages = "; ".join(
            f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        raise ValidationError(messages) from exc
