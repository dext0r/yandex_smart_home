"""Base class for API response schemas."""
from typing import Any

from pydantic import BaseModel
from pydantic.generics import GenericModel


class APIModel(BaseModel):
    """Base API response model."""

    def as_json(self) -> str:
        """Generate a JSON representation of the model."""
        return super().json(exclude_none=True, ensure_ascii=False)

    def as_dict(self) -> dict[str, Any]:
        """Generate a dictionary representation of the model."""
        return super().dict(exclude_none=True)


class GenericAPIModel(GenericModel, APIModel):
    """Base generic API response model."""
