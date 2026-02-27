"""Schema for range capability.
https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range.html
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, computed_field

from .base import APIModel


class RangeCapabilityUnit(StrEnum):
    """Unit used in a range capability."""

    PERCENT = "unit.percent"
    TEMPERATURE_CELSIUS = "unit.temperature.celsius"


class RangeCapabilityInstance(StrEnum):
    """Instance of a range capability.
    https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html
    """

    BRIGHTNESS = "brightness"
    CHANNEL = "channel"
    HUMIDITY = "humidity"
    OPEN = "open"
    TEMPERATURE = "temperature"
    VOLUME = "volume"


class RangeCapabilityRange(APIModel):
    """Value range of a range capability."""

    min: float
    max: float
    precision: float

    def __str__(self) -> str:
        return f"[{self.min}, {self.max}]"


class RangeCapabilityParameters(APIModel):
    """Parameters of a range capability."""

    instance: RangeCapabilityInstance
    unit: Optional[RangeCapabilityUnit] = Field(default=None, exclude=True)  # исключаем из сериализации, если нужно
    random_access: bool
    range: Optional[RangeCapabilityRange] = Field(default=None)

    @computed_field
    @property
    def computed_unit(self) -> RangeCapabilityUnit:
        """Вычисляемый unit на основе instance."""
        match self.instance:
            case RangeCapabilityInstance.BRIGHTNESS:
                return RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.HUMIDITY:
                return RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.OPEN:
                return RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.TEMPERATURE:
                return RangeCapabilityUnit.TEMPERATURE_CELSIUS
            case _:
                return self.unit or RangeCapabilityUnit.PERCENT  # fallback

    @model_validator(mode='after')
    def validate_range(self) -> Self:
        """Force range boundaries for a capability instance."""
        r = self.range
        if r:
            match self.instance:
                case RangeCapabilityInstance.HUMIDITY | RangeCapabilityInstance.OPEN:
                    r.min = max(0.0, r.min)
                    r.max = min(100.0, r.max)
                case RangeCapabilityInstance.BRIGHTNESS:
                    r.min = max(0.0, min(1.0, r.min))
                    r.max = 100.0
                    r.precision = 1.0
        else:
            if self.instance in (
                RangeCapabilityInstance.BRIGHTNESS,
                RangeCapabilityInstance.HUMIDITY,
                RangeCapabilityInstance.OPEN,
                RangeCapabilityInstance.TEMPERATURE,
            ):
                raise ValueError(f"range field required for {self.instance}")

        return self


class RangeCapabilityInstanceActionState(APIModel):
    """New value for a range capability."""

    instance: RangeCapabilityInstance
    value: float
    relative: bool = False

    @field_validator("relative", mode="before")
    @classmethod
    def set_relative(cls, v: Any) -> bool:
        """Update relative value."""
        return False if v is None else v