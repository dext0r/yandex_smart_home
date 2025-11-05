"""Base class for API response schemas."""

from typing import Any

from pydantic import BaseModel


class APIModel(BaseModel):
    """Base API response model."""

    def as_json(self) -> str:
        """Generate a JSON representation of the model."""
        return super().model_dump_json(exclude_none=True, ensure_ascii=False, serialize_as_any=True)

    def as_dict(self) -> dict[str, Any]:
        """Generate a dictionary representation of the model."""
        return super().model_dump(exclude_none=True)
