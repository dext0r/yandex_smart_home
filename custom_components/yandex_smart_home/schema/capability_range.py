"""Schema for range capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range.html
"""

from enum import StrEnum
from typing import Any

from pydantic import root_validator, validator

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
    unit: RangeCapabilityUnit | None = None
    random_access: bool
    range: RangeCapabilityRange | None = None

    @root_validator
    def compute_unit(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Return value unit for a capability instance."""
        match values.get("instance"):
            case RangeCapabilityInstance.BRIGHTNESS:
                values["unit"] = RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.HUMIDITY:
                values["unit"] = RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.OPEN:
                values["unit"] = RangeCapabilityUnit.PERCENT
            case RangeCapabilityInstance.TEMPERATURE:
                values["unit"] = RangeCapabilityUnit.TEMPERATURE_CELSIUS

        return values

    @root_validator
    def validate_range(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Force range boundaries for a capability instance."""

        r: RangeCapabilityRange | None
        if r := values.get("range"):
            match values.get("instance"):
                case RangeCapabilityInstance.HUMIDITY | RangeCapabilityInstance.OPEN:
                    r.min, r.max = max([0.0, r.min]), min([100.0, r.max])
                case RangeCapabilityInstance.BRIGHTNESS:
                    r.min = max(min(r.min, 1.0), 0.0)
                    r.max = 100.0
                    r.precision = 1.0

        return values


class RangeCapabilityInstanceActionState(APIModel):
    """New value for a range capability."""

    instance: RangeCapabilityInstance
    value: float
    relative: bool = False

    @validator("relative", pre=True, always=True)
    def set_relative(cls, v: Any) -> Any:
        """Update relative value."""
        if v is None:  # VK
            return False

        return v
