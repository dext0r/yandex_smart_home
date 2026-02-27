"""Base class for API response schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, model_serializer

T = TypeVar("T")


class APIModel(BaseModel):
    """Base API response model."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        # strict=False,  # можно включить, если нужно более строгое приведение типов
    )

    @model_serializer(mode="wrap")
    def serialize(self, handler, info):
        """Serialize model excluding None values."""
        dumped = handler(self)
        if info.mode == "json":
            # для json() — исключаем None и используем ensure_ascii=False
            return {k: v for k, v in dumped.items() if v is not None}
        return dumped

    def as_dict(self) -> dict[str, Any]:
        """Generate a dictionary representation of the model (exclude None)."""
        return self.model_dump(exclude_none=True, by_alias=False)

    def as_json(self) -> str:
        """Generate a JSON representation of the model (exclude None, ensure_ascii=False)."""
        return self.model_dump_json(exclude_none=True, ensure_ascii=False)


class GenericAPIModel(APIModel, Generic[T]):
    """Base generic API response model."""

    # В pydantic v2 GenericModel больше не нужен — достаточно Generic + BaseModel
    # Если нужно что-то специфическое — добавляй поля/валидаторы здесь
    pass