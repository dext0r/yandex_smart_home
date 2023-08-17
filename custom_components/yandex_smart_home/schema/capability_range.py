"""Schema for range capability.

https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range.html
"""
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, root_validator


class RangeCapabilityUnit(StrEnum):
    PERCENT = "unit.percent"
    TEMPERATURE_CELSIUS = "unit.temperature.celsius"


class RangeCapabilityInstance(StrEnum):
    """https://yandex.ru/dev/dialogs/smart-home/doc/concepts/range-instance.html"""

    BRIGHTNESS = "brightness"
    CHANNEL = "channel"
    HUMIDITY = "humidity"
    OPEN = "open"
    TEMPERATURE = "temperature"
    VOLUME = "volume"


class RangeCapabilityRange(BaseModel):
    min: float
    max: float
    precision: float

    def __str__(self):
        return f"[{self.min}, {self.max}]"


class RangeCapabilityParameters(BaseModel):
    instance: RangeCapabilityInstance
    unit: RangeCapabilityUnit | None
    random_access: bool
    range: RangeCapabilityRange | None

    @root_validator
    def compute_unit(cls, values: dict[str, Any]) -> dict[str, Any]:
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


class RangeCapabilityInstanceActionState(BaseModel):
    instance: RangeCapabilityInstance
    value: float
    relative: bool = False
